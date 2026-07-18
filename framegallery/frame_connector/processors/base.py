"""Interface and shared implementation for the pluggable upload processors."""

from __future__ import annotations

import abc
import asyncio
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from blinker import signal
from icmplib import ping
from samsungtvws.async_remote import SamsungTVWSAsyncRemote

from framegallery.aspect_ratio import get_aspect_ratio
from framegallery.config import settings
from framegallery.logging_config import setup_logging

if TYPE_CHECKING:
    from framegallery.libraries.base import PhotoBytes, PhotoRef
    from framegallery.libraries.manager import LibraryManager

# The Samsung art-mode API version we report on /api/status. Kept here so all
# processors (and main.py) share a single source of truth.
api_version = "4.3.4.0"

logger = setup_logging(
    log_level=settings.log_level,
    websocket_log_level=settings.websocket_log_level,
    logs_path=settings.logs_path,
)


class ProcessorKind(str, Enum):
    """The available upload-processor strategies (see ``settings.upload_processor``)."""

    SINGLE_ASYNC = "single_async"
    BATCH_SLIDESHOW = "batch_slideshow"
    SYNC_THREAD = "sync_thread"


class TvNotConnectedError(Exception):
    """Raised when an operation is attempted while the TV is not connected."""


class TvConnectionTimeoutError(TvNotConnectedError):
    """Raised when the TV connection times out."""


class UploadProcessor(abc.ABC):
    """
    Strategy that owns the TV connection and applies active-image changes.

    Exactly one processor is built at startup from ``settings.upload_processor``.
    It owns its own TV connection and is the sole subscriber to the
    ``active_image_updated`` blinker signal; the other signal receivers
    (config + SSE listeners) are unaffected by the chosen strategy.

    This base class provides the transport-agnostic machinery shared by every
    strategy: the ICMP reconnection pinger, token pairing, photo-byte resolution,
    matte selection, and signal wiring. Subclasses own the actual TV client
    (async or sync) and implement the abstract methods below.
    """

    kind: ProcessorKind

    IDEAL_ASPECT_RATIO_WIDTH = 16
    IDEAL_ASPECT_RATIO_HEIGHT = 9

    def __init__(self, ip_address: str, port: int, library_manager: LibraryManager | None = None) -> None:
        self._ip_address = ip_address
        self._port = port
        # Persist the auth token in the data directory (a mounted volume in
        # Docker) under a stable filename so it survives restarts.
        self._token_file = Path(settings.data_path) / "tv-token.txt"
        # Set during application startup; used to resolve photo bytes from any library.
        self.library_manager: LibraryManager | None = library_manager

        self._background_tasks: set[asyncio.Task] = set()
        self._pinger_task: asyncio.Task | None = None
        self._shutting_down = False
        self._tv_is_online = False
        self._connected = False
        self._latest_content_id: str | None = None

        self._active_image_updated_signal = signal("active_image_updated")

        # Check if the TV is available on the network; if so the connection sequence starts.
        self._start_reconnection_pinger()

    # --- lifecycle ---

    @property
    def is_connected(self) -> bool:
        """Whether the processor currently has a live, usable TV connection."""
        return self._connected and self._tv_is_online

    @abc.abstractmethod
    async def open(self) -> None:
        """Establish/verify the TV connection and start listening. Idempotent."""

    @abc.abstractmethod
    async def close(self) -> None:
        """Tear down the TV connection cleanly. Idempotent."""

    @abc.abstractmethod
    async def reconnect(self) -> None:
        """(Re)build the TV client and open the connection."""

    # --- the hot path ---

    @abc.abstractmethod
    async def apply_active_image(self, photo: PhotoRef) -> None:
        """
        React to a request to make ``photo`` the active image.

        - single_async / sync_thread: upload -> select_image -> delete previous.
        - batch_slideshow: ensure the photo is resident / top up the batch (the TV
          rotates on its own, so this need not change the on-screen image).
        """

    # --- generic TV file ops (used by TvCleanupService and the tv_files router) ---

    @abc.abstractmethod
    async def list_files(self, category: str = "MY-C0002") -> list[dict] | None:
        """List files on the TV for a category, or None if the TV is unavailable."""

    @abc.abstractmethod
    async def delete_files(self, content_ids: list[str]) -> dict[str, bool] | None:
        """Delete files from the TV, returning per-id success, or None if unavailable."""

    # --- optional diagnostics ---

    async def get_active_item_details(self) -> dict | None:
        """Return the TV's current active item, if the processor supports it."""
        return None

    async def shutdown(self) -> None:
        """
        Tear down for application shutdown.

        Cancels the reconnection pinger and closes the connection *without* re-arming
        the pinger (``close()`` re-arms it during normal operation, but a restart
        mid-shutdown would leave a pending task and trigger reconnect attempts as the
        app stops). Call this from the lifespan teardown instead of ``close()``.
        """
        self._shutting_down = True
        for task in list(self._background_tasks):
            task.cancel()
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        await self.close()

    # --- shared machinery (transport-agnostic) ---

    def _start_reconnection_pinger(self) -> None:
        """
        Start the reconnection timer that reconnects once the TV is reachable.

        Idempotent: does nothing while shutting down, or if a pinger is already
        running. ``close()`` and the error paths both call this, so without the
        guard overlapping calls would spawn multiple concurrent pingers.
        """
        if self._shutting_down:
            return
        if self._pinger_task is not None and not self._pinger_task.done():
            return
        logger.info("Starting reconnection timer")
        pinger = asyncio.create_task(self._reconnect_ping())
        self._pinger_task = pinger
        self._background_tasks.add(pinger)
        pinger.add_done_callback(self._background_tasks.discard)

    async def _reconnect_ping(self) -> None:
        """Ping the TV until it is online, then reconnect once and stop."""
        while True:
            try:
                # icmplib.ping() is blocking, so run it in a worker thread to avoid
                # stalling the event loop (up to the ping timeout) on every cycle.
                response = await asyncio.to_thread(ping, self._ip_address, count=1, timeout=2, privileged=False)
                if not response.is_alive:
                    logger.debug("Ping to %s failed, retrying in 10 seconds", self._ip_address)
                    self._tv_is_online = False
                else:
                    logger.info("Ping to %s successful, reconnecting to the TV.", self._ip_address)
                    self._tv_is_online = True
                    await self.reconnect()
                    break
            except Exception:
                logger.exception("Error during ping.")
            await asyncio.sleep(10)

    async def _ensure_token(self) -> None:
        """
        Ensure a valid auth token is persisted before opening the art channel.

        Recent Frame firmware (incl. 2023 models after an OS update) no longer
        completes first-time pairing on the art-app channel: it just times out
        with `ms.channel.timeOut`. The token must instead be obtained on the
        standard remote-control channel, which shows the on-screen "Allow"
        prompt and returns a token we can reuse for the art-app channel.

        On the very first run the user must accept the prompt on the TV; the
        token is then written to `self._token_file` and reused silently after.
        """
        remote = SamsungTVWSAsyncRemote(
            host=self._ip_address,
            port=self._port,
            name=settings.tv_client_name,
            token_file=str(self._token_file),
            timeout=30,
        )
        try:
            # open() triggers the prompt (first run) and persists the token via
            # the base connection's _check_for_token on ms.channel.connect.
            await remote.open()
        finally:
            await remote.close()

    async def _fetch_photo_bytes(self, photo: PhotoRef) -> PhotoBytes | None:
        """Resolve the raw image bytes for a photo through the library manager."""
        if self.library_manager is None:
            logger.error("Processor has no library_manager; cannot fetch photo bytes.")
            return None
        try:
            return await self.library_manager.fetch_bytes(photo.composite_id)
        except Exception:
            logger.exception("Failed to fetch bytes for photo %s", photo.composite_id)
            return None

    def _transform_file_data(self, file_data: dict) -> dict:
        """Transform a raw TV file entry into our standardized shape."""
        content_id = file_data.get("content_id", "Unknown")

        # Determine file type from content_type and other indicators.
        content_type = file_data.get("content_type", "mobile")
        file_type = "SAMSUNG_ART" if content_type == "preinstall" else "JPEG"

        file_info = {
            "content_id": content_id,
            "category_id": file_data.get("category_id"),
            "file_name": content_id,
            "file_type": file_type,
            "file_size": file_data.get("file_size"),
            "date": file_data.get("image_date"),
            "thumbnail_available": True,  # Frame TV typically has thumbnails for all images
            "matte": file_data.get("matte_id"),
        }

        # Include any additional metadata fields from the TV.
        for key, value in file_data.items():
            if key not in file_info:
                file_info[key] = value

        return file_info

    def _filter_files_by_category(self, files: list[dict], category: str | None) -> list[dict]:
        """Filter raw TV files by category and transform them into our shape."""
        return [
            self._transform_file_data(file_data)
            for file_data in files
            if file_data.get("category_id") == category or category is None
        ]

    def _compute_matte(self, photo_bytes: PhotoBytes) -> str:
        """
        Pick the matte from the final (post-crop) dimensions.

        A 16:9 photo needs no matte; anything else (or unknown dimensions) gets a
        shadowbox so it isn't stretched.
        """
        if photo_bytes.width and photo_bytes.height:
            aspect_width, aspect_height = get_aspect_ratio(photo_bytes.width, photo_bytes.height)
            if aspect_width == self.IDEAL_ASPECT_RATIO_WIDTH and aspect_height == self.IDEAL_ASPECT_RATIO_HEIGHT:
                return "none"
        return "shadowbox_black"

    def _on_active_image_signal_connect(self) -> None:
        """Subscribe to the active_image_updated signal."""
        self._active_image_updated_signal.connect(self._on_active_image_signal)

    def _on_active_image_signal_disconnect(self) -> None:
        """Unsubscribe from the active_image_updated signal."""
        self._active_image_updated_signal.disconnect(self._on_active_image_signal)

    async def _on_active_image_signal(self, _: object, active_photo: PhotoRef) -> None:
        """Blinker signal adapter: route the active_image_updated signal to apply_active_image."""
        await self.apply_active_image(active_photo)
