"""
The ``sync_thread`` upload processor (Docent-style).

Same one-image-at-a-time behaviour as ``single_async`` (upload -> select_image ->
delete previous), but driven through the *synchronous* ``samsungtvws`` client run in
a background thread via ``asyncio.to_thread``. It adds the reliability plumbing that
the Docent project uses to survive a flaky Frame:

- all TV I/O is serialised behind an ``asyncio.Lock`` (the sync client is not
  concurrency-safe);
- the connection is proactively closed + reopened after ~30 s idle (the Frame
  silently drops idle sockets, after which the next call hangs);
- a Wake-on-LAN packet is sent before retrying (when ``tv_mac_address`` is set);
- operations are retried a bounded number of times with backoff.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

from samsungtvws.exceptions import ResponseError
from samsungtvws.remote import SamsungTVWS

from framegallery.config import settings
from framegallery.frame_connector.processors.base import (
    ProcessorKind,
    TvConnectionTimeoutError,
    UploadProcessor,
)
from framegallery.logging_config import setup_logging

if TYPE_CHECKING:
    from collections.abc import Callable

    from samsungtvws.art import SamsungTVArt

    from framegallery.libraries.base import PhotoRef

logger = setup_logging(
    log_level=settings.log_level,
    websocket_log_level=settings.websocket_log_level,
    logs_path=settings.logs_path,
)


class SyncThreadProcessor(UploadProcessor):
    """Push one active image at a time via the synchronous client run in a thread."""

    kind = ProcessorKind.SYNC_THREAD

    # Close + reopen the connection if it has been idle longer than this (seconds).
    IDLE_RECYCLE_SECONDS = 30
    # Socket/handshake timeout for the sync client (seconds).
    CONNECT_TIMEOUT = 10
    # Per-operation timeouts (seconds).
    UPLOAD_TIMEOUT = 120
    OP_TIMEOUT = 20
    # Retry policy.
    MAX_ATTEMPTS = 3
    RETRY_DELAY = 2

    def __init__(self, ip_address: str, port: int, library_manager=None) -> None:  # noqa: ANN001
        super().__init__(ip_address, port, library_manager)
        self._remote: SamsungTVWS | None = None
        self._art: SamsungTVArt | None = None
        self._op_lock = asyncio.Lock()
        self._last_used = 0.0

    # --- lifecycle ---

    async def open(self) -> None:
        """Connect the sync client (in a thread) and subscribe to slideshow updates."""
        if not self._tv_is_online:
            return
        await self._connect_client()
        self._connected = True
        self._on_active_image_signal_connect()

    async def close(self) -> None:
        """Close the connection and (re)start the reconnection pinger."""
        await self._close_client()
        self._connected = False
        self._on_active_image_signal_disconnect()
        self._start_reconnection_pinger()

    async def reconnect(self) -> None:
        """Ensure a token, then (re)open the connection."""
        await self._ensure_token()
        await self.open()

    # --- connection management (all blocking work off the event loop) ---

    async def _connect_client(self) -> None:
        """Build and open the synchronous client in a worker thread."""

        def _build() -> tuple[SamsungTVWS, SamsungTVArt]:
            remote = SamsungTVWS(
                host=self._ip_address,
                port=self._port,
                token_file=str(self._token_file),
                name=settings.tv_client_name,
                timeout=self.CONNECT_TIMEOUT,
            )
            art = remote.art()
            art.open()
            return remote, art

        self._remote, self._art = await asyncio.to_thread(_build)
        self._last_used = time.monotonic()
        logger.info("sync_thread: connected to TV at %s", self._ip_address)

    async def _close_client(self) -> None:
        """Close the synchronous client in a worker thread (idempotent)."""
        remote = self._remote
        self._remote = None
        self._art = None
        if remote is not None:
            try:
                await asyncio.to_thread(remote.close)
            except Exception:
                logger.exception("sync_thread: error closing TV client")

    async def _ensure_live_client(self) -> None:
        """Ensure a live client, recycling it if it has been idle too long."""
        if self._art is None:
            await self._connect_client()
            return
        if time.monotonic() - self._last_used > self.IDLE_RECYCLE_SECONDS:
            logger.debug("sync_thread: recycling idle connection (idle > %ds)", self.IDLE_RECYCLE_SECONDS)
            await self._close_client()
            await self._connect_client()

    def _wake_tv(self) -> None:
        """Send a Wake-on-LAN packet if a TV MAC address is configured."""
        mac = settings.tv_mac_address
        if not mac:
            return
        try:
            from wakeonlan import send_magic_packet  # noqa: PLC0415

            send_magic_packet(mac)
            logger.info("sync_thread: sent Wake-on-LAN packet to %s", mac)
        except Exception:
            logger.exception("sync_thread: failed to send Wake-on-LAN packet")

    async def _run_tv_op(self, fn: Callable[[SamsungTVArt], Any], *, description: str, timeout: float) -> Any:  # noqa: ANN401, ASYNC109
        """
        Run a blocking TV operation in a thread, with recycle + bounded retries.

        Only one operation runs at a time (the sync client isn't concurrency-safe).
        A ``ResponseError`` is a definitive TV rejection and is not retried.
        """
        async with self._op_lock:
            last_exc: Exception | None = None
            for attempt in range(1, self.MAX_ATTEMPTS + 1):
                try:
                    await self._ensure_live_client()
                    assert self._art is not None  # noqa: S101 -- guaranteed by _ensure_live_client
                    result = await asyncio.wait_for(asyncio.to_thread(fn, self._art), timeout)
                    self._last_used = time.monotonic()
                except ResponseError:
                    # Definitive rejection from the TV (e.g. unsupported matte); don't retry.
                    raise
                except Exception as exc:  # noqa: BLE001 -- retry on any transient TV/socket failure
                    last_exc = exc
                    logger.warning(
                        "sync_thread: TV op '%s' failed (attempt %d/%d): %s",
                        description,
                        attempt,
                        self.MAX_ATTEMPTS,
                        exc,
                    )
                    await self._close_client()
                    if attempt < self.MAX_ATTEMPTS:
                        if attempt == 1:
                            self._wake_tv()
                        await asyncio.sleep(self.RETRY_DELAY * attempt)
                else:
                    return result

            logger.error("sync_thread: TV op '%s' giving up after %d attempts", description, self.MAX_ATTEMPTS)
            if isinstance(last_exc, TimeoutError):
                raise TvConnectionTimeoutError from last_exc
            if last_exc is not None:
                raise last_exc
            return None

    # --- the hot path ---

    async def apply_active_image(self, photo: PhotoRef) -> None:
        """Upload the given photo to the TV, activate it, and delete the previous one."""
        if not self._connected:
            return

        logger.info("sync_thread: updating active image on TV: %s", photo.composite_id)

        photo_bytes = await self._fetch_photo_bytes(photo)
        if photo_bytes is None:
            return
        matte = self._compute_matte(photo_bytes)
        file_data = photo_bytes.data
        file_type = photo_bytes.file_type_suffix

        try:
            data = await self._run_tv_op(
                lambda art: art.upload(file_data, file_type=file_type, matte=matte, portrait_matte="none"),
                description=f"upload {photo.composite_id}",
                timeout=self.UPLOAD_TIMEOUT,
            )
        except Exception:
            logger.exception("sync_thread: upload failed for %s", photo.composite_id)
            return

        if not data or not data.get("content_id"):
            logger.error("sync_thread: upload completed but did not return a content_id.")
            return

        content_id = data["content_id"]
        try:
            await self._run_tv_op(
                lambda art: art.select_image(content_id, "MY-C0002"),
                description=f"select {content_id}",
                timeout=self.OP_TIMEOUT,
            )
            if self._latest_content_id is not None:
                await self._run_tv_op(
                    lambda art: art.delete(self._latest_content_id),
                    description=f"delete {self._latest_content_id}",
                    timeout=self.OP_TIMEOUT,
                )
            self._latest_content_id = content_id
        except Exception:
            logger.exception("sync_thread: activate/cleanup failed for %s", content_id)

    async def get_active_item_details(self) -> dict | None:
        """Get the current active item details from the TV."""
        if not self._connected:
            return None
        try:
            return await self._run_tv_op(
                lambda art: art.get_current(), description="get_current", timeout=self.OP_TIMEOUT
            )
        except Exception:
            logger.exception("sync_thread: failed to get current active item")
            return None

    # --- generic TV file ops ---

    async def list_files(self, category: str = "MY-C0002") -> list[dict] | None:
        """List files on the TV for a category, or None if the TV is unavailable."""
        if not self._connected:
            logger.error("sync_thread: TV not connected, cannot list files.")
            return None
        try:
            available_files = await self._run_tv_op(
                lambda art: art.available(category), description="available", timeout=self.OP_TIMEOUT
            )
        except TvConnectionTimeoutError:
            raise
        except Exception:
            logger.exception("sync_thread: error retrieving file list from TV")
            return None

        if not available_files:
            return []
        return self._filter_files_by_category(available_files, category)

    async def delete_files(self, content_ids: list[str]) -> dict[str, bool] | None:
        """Delete files from the TV in chunks, returning per-id success."""
        if not self._connected:
            logger.error("sync_thread: TV not connected, cannot delete files.")
            return None
        if not content_ids:
            return {}

        chunk_size = 20
        result: dict[str, bool] = {}
        try:
            for i in range(0, len(content_ids), chunk_size):
                chunk = content_ids[i : i + chunk_size]
                await self._run_tv_op(
                    lambda art, c=chunk: art.delete_list(c),
                    description=f"delete_list ({len(chunk)})",
                    timeout=self.OP_TIMEOUT,
                )
                result.update(dict.fromkeys(chunk, True))
        except TvConnectionTimeoutError:
            raise
        except Exception as exc:
            logger.exception("sync_thread: error deleting files from TV")
            error_msg = str(exc).lower()
            if any(term in error_msg for term in ["not found", "does not exist", "invalid"]):
                return dict.fromkeys(content_ids, False)
            return None
        return result
