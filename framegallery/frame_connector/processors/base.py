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
from samsungtvws.rest import SamsungTVRest

from framegallery.aspect_ratio import get_aspect_ratio
from framegallery.config import settings
from framegallery.logging_config import setup_logging
from framegallery.repository.config_repository import (
    ConfigKey,
    read_bool_setting,
    read_json_setting,
    read_str_setting,
    write_setting,
)

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
    # Timeout (seconds) for the REST power-state probe. Short: it is a LAN request to
    # a TV that is either answering promptly or not answering at all.
    REST_TIMEOUT = 5
    # The only TV port that speaks TLS and token auth. samsungtvws derives the whole
    # transport from the port number -- ws:// vs wss://, whether the URL carries a
    # token, http vs https for REST, and the SSL options -- by testing for exactly
    # this value, so it is the single thing that distinguishes the two modes.
    SECURE_PORT = 8002
    # How many previously uploaded images to delete in one batched call per cycle, and
    # the cap on the backlog we are prepared to remember.
    PENDING_DELETION_BATCH = 20
    MAX_PENDING_DELETIONS = 200

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

        # Bookkeeping for images we have put on the TV, restored from the database so
        # a restart does not abandon them. Before this was persisted, every restart
        # stranded whichever image was live at the time: still on the TV, with nothing
        # left able to identify or delete it. That was the largest single source of
        # images the app lost track of.
        self._latest_content_id: str | None = read_str_setting(ConfigKey.LATEST_TV_CONTENT_ID, default=None)
        self._pending_deletions: list[str] = self._load_pending_deletions()
        if self._pending_deletions:
            logger.info(
                "Restored %d TV image(s) still awaiting deletion: %s",
                len(self._pending_deletions),
                self._pending_deletions,
            )

        # Last known art-mode state, refreshed by the ArtModeWatchdog and after our
        # own writes. None means "not established yet"; see art_mode_permits_upload().
        self._art_mode_active: bool | None = None

        # Deduplicate the reconnection-failure logging: a wedged TV can fail every
        # 10s for hours, so only the first occurrence of a given error gets a full
        # traceback; repeats are collapsed to a single-line warning.
        self._reconnect_failures = 0
        self._last_reconnect_error: str | None = None

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

    # --- TV content bookkeeping ---

    def _load_pending_deletions(self) -> list[str]:
        """Restore the pending-deletion list, tolerating anything unexpected on disk."""
        stored = read_json_setting(ConfigKey.PENDING_TV_DELETIONS, default=[])
        if not isinstance(stored, list):
            logger.warning("Stored pending TV deletions were not a list (%r); starting empty", stored)
            return []
        return [item for item in stored if isinstance(item, str)]

    def _persist_tracked_content(self) -> None:
        """Persist the content bookkeeping, so a restart resumes where we left off."""
        write_setting(ConfigKey.LATEST_TV_CONTENT_ID, self._latest_content_id)
        write_setting(ConfigKey.PENDING_TV_DELETIONS, self._pending_deletions)

    def record_uploaded(self, content_id: str) -> None:
        """
        Adopt a freshly uploaded image as the current one, queueing the previous for deletion.

        Called *immediately* after a successful upload, before select_image. The
        ordering is the point: previously this assignment sat at the end of the
        select-then-delete block, so any failure in between skipped it and left the
        new image on the TV with nothing tracking it. Recording first means every
        image we put on the TV is accounted for, whatever happens next.
        """
        previous = self._latest_content_id
        self._latest_content_id = content_id
        if previous is not None and previous != content_id:
            self._queue_for_deletion(previous)
        self._persist_tracked_content()

    def _queue_for_deletion(self, content_id: str) -> None:
        """Add an id to the pending-deletion list, keeping it deduplicated and bounded."""
        if content_id in self._pending_deletions:
            return
        self._pending_deletions.append(content_id)
        if len(self._pending_deletions) > self.MAX_PENDING_DELETIONS:
            # Deletes have been failing for a very long time; drop the oldest rather
            # than growing without bound. The TV auto-cleanup service is the backstop
            # for anything that falls out here.
            dropped = self._pending_deletions[: -self.MAX_PENDING_DELETIONS]
            self._pending_deletions = self._pending_deletions[-self.MAX_PENDING_DELETIONS :]
            logger.error(
                "Pending TV deletions exceeded %d; dropped %d id(s) that will need the "
                "auto-cleanup sweep to remove: %s",
                self.MAX_PENDING_DELETIONS,
                len(dropped),
                dropped,
            )

    async def drain_pending_deletions(self) -> None:
        """
        Delete the images we still owe the TV a delete for.

        Uses a single batched delete rather than one command per image: every extra
        command is another chance to wedge the Frame, and a wedged Frame is precisely
        what leaves images behind. Ids that fail stay queued and are retried on the
        next cycle, so a transient failure heals itself instead of orphaning.
        """
        if not self._pending_deletions:
            return

        # Settle here rather than at the call site so an empty queue costs nothing:
        # tv_command_delay is measured in seconds, so pausing before a no-op would add
        # that delay to every single slideshow tick.
        await self._settle()

        batch = self._pending_deletions[: self.PENDING_DELETION_BATCH]
        logger.info("Deleting %d previously uploaded TV image(s): %s", len(batch), batch)
        try:
            results = await self.delete_files(batch)
        except Exception:
            logger.exception("Batched delete of previous TV images failed; will retry next cycle")
            return

        if results is None:
            logger.warning("TV unavailable while deleting previous images; will retry next cycle")
            return

        deleted = {content_id for content_id, ok in results.items() if ok}
        if deleted:
            self._pending_deletions = [c for c in self._pending_deletions if c not in deleted]
            self._persist_tracked_content()
        failed = set(batch) - deleted
        if failed:
            logger.warning("Could not delete %d TV image(s); still queued: %s", len(failed), sorted(failed))

    # --- art mode ---

    @property
    def art_mode_active(self) -> bool | None:
        """Last known art-mode state, or None if it has not been established yet."""
        return self._art_mode_active

    def note_art_mode(self, *, active: bool | None) -> None:
        """Record the art-mode state observed by the watchdog or a post-write check."""
        self._art_mode_active = active

    def tv_watch_mode_enabled(self) -> bool:
        """
        Whether the user has explicitly claimed the TV to watch television.

        Read live from the database on every call rather than cached, so toggling it
        in the UI takes effect on the next push instead of at the next poll.
        """
        return read_bool_setting(ConfigKey.TV_WATCH_MODE_ENABLED, default=False)

    def art_mode_permits_upload(self) -> bool:
        """
        Whether pushing an image to the TV is worthwhile right now.

        TV watch mode is a hard stop: the user has said the TV is theirs, so the app
        stays off it entirely regardless of what art mode reports. This is checked
        first precisely so the toggle does not depend on art-mode detection being
        accurate or up to date.

        Failing that, only a *known* art-mode "off" suppresses the push: while the TV
        is showing regular television our uploads are invisible, and issuing them is
        what tends to wedge the Frame in the first place. An unknown state (nothing has
        polled yet, or the query failed) stays permissive so a watchdog problem can
        never silently freeze the slideshow.
        """
        if self.tv_watch_mode_enabled():
            return False
        return self._art_mode_active is not False

    async def get_art_mode(self) -> bool | None:
        """
        Return whether the TV is in art mode, or None if it cannot be determined.

        None specifically means "we could not ask" -- the art channel is unreachable
        -- which is a different condition from a confident False, and the watchdog
        treats the two very differently. Processors that own an art client override
        this; the default reports "unknown".
        """
        return None

    async def set_art_mode(self, *, enabled: bool) -> bool:
        """
        Ask the TV to enter or leave art mode; return whether the command was accepted.

        Overridden by processors that own an art client.
        """
        _ = enabled
        return False

    async def is_tv_powered_on(self) -> bool | None:
        """
        Report the TV's power state over REST, or None if it is unreachable.

        This deliberately avoids the art WebSocket: it is a plain HTTP GET to
        ``/api/v2/``, so it still answers when the art channel has wedged. That makes
        it the only probe that can tell "the whole TV is gone" apart from "the TV is
        fine but art mode has crashed". ICMP is not a substitute -- a Frame in standby
        still replies to ping.
        """

        def _probe() -> bool:
            rest = SamsungTVRest(self._ip_address, self._port, self.REST_TIMEOUT)
            return rest.rest_power_state()

        try:
            return await asyncio.to_thread(_probe)
        except Exception:  # noqa: BLE001 -- any failure here means "unreachable", by design
            logger.debug("REST power-state probe failed for %s", self._ip_address, exc_info=True)
            return None

    async def verify_art_mode_after_write(self) -> None:
        """
        Re-check art mode straight after our own TV writes, and restore it if it dropped.

        This is the only path that force-enables art mode, and the timing is the whole
        point: finding it off immediately after our upload/select/delete sequence means
        *we* knocked the Frame out of art mode, so turning it back on cannot be fighting
        someone who just picked up the remote. The periodic watchdog deliberately never
        does this -- between writes an "off" is indistinguishable from a person choosing
        to watch television, and the safe assumption there is that a human did it.
        """
        active = await self.get_art_mode()
        self.note_art_mode(active=active)
        if active is not False:
            return

        # TV watch mode is an explicit instruction to leave the TV alone. Honour it
        # even here, where we know we caused the drop: the user would rather keep
        # watching than have the app claw the screen back.
        if self.tv_watch_mode_enabled():
            logger.info("Art mode is off after our write, but TV watch mode is on; leaving the TV alone.")
            return

        logger.warning(
            "Art mode dropped during our own TV commands -- the Frame fell back to "
            "regular TV. Attempting to restore art mode."
        )
        if not await self.set_art_mode(enabled=True):
            logger.error("Failed to restore art mode after write; the TV is left on regular TV.")
            return

        # The TV accepting set_artmode is not the same as it acting on it, so confirm
        # rather than assuming -- otherwise a Frame that is wedged badly enough to
        # ignore the command would still be reported as recovered.
        restored = await self.get_art_mode()
        self.note_art_mode(active=restored)
        if restored:
            logger.info("Art mode restored after write.")
        else:
            logger.error(
                "Art mode restore was accepted but the TV is still not in art mode (now %s); it is left on regular TV.",
                restored,
            )

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
        # Fresh campaign: the first failure below should always get a full traceback.
        self._reconnect_failures = 0
        self._last_reconnect_error = None
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
                    self._reconnect_failures = 0
                    self._last_reconnect_error = None
                    break
            except Exception as exc:  # noqa: BLE001 -- retry loop must survive any connection error
                self._log_reconnect_failure(exc)
            await asyncio.sleep(10)

    def _log_reconnect_failure(self, exc: Exception) -> None:
        """
        Log a reconnection failure, collapsing repeats to avoid traceback spam.

        A wedged TV can reject the connection every 10s indefinitely. The first
        occurrence of a given error is logged with a full traceback; identical
        repeats are collapsed to a single-line warning with a running count.
        """
        signature = f"{type(exc).__name__}: {exc}"
        if signature != self._last_reconnect_error:
            self._last_reconnect_error = signature
            self._reconnect_failures = 1
            logger.exception("Error connecting to TV; will keep retrying every 10s.")
        else:
            self._reconnect_failures += 1
            logger.warning(
                "Still unable to connect to TV after %d attempts (%s); retrying every 10s.",
                self._reconnect_failures,
                signature,
            )

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

        Only ``SECURE_PORT`` uses token auth. On the plain-WebSocket port the art
        URL carries no token parameter at all, so pairing has nothing to
        accomplish -- and the remote-control channel there rejects unauthenticated
        clients outright with ``ms.channel.unauthorized``, which would abort every
        reconnect and leave the app permanently disconnected.
        """
        if self._port != self.SECURE_PORT:
            logger.debug(
                "Port %s uses plain WebSockets without token auth; skipping pairing.",
                self._port,
            )
            return

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

    async def _settle(self) -> None:
        """
        Pause briefly between consecutive TV commands.

        The Frame needs a moment to finish digesting an upload before it will
        reliably accept the follow-up ``select_image``/``delete``; issuing them
        back-to-back can crash Art Mode back to regular TV. Controlled by
        ``settings.tv_command_delay`` (seconds); a value of 0 disables the pause.
        """
        if settings.tv_command_delay > 0:
            await asyncio.sleep(settings.tv_command_delay)

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
