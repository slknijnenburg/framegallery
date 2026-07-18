"""
The ``batch_slideshow`` upload processor.

Instead of pushing one active image on every slideshow tick, this uploads a batch of
images to the TV's internal storage once and hands rotation to the TV's own slideshow
API. The app then steps back: the periodic slideshow loop is suppressed for this mode
(see ``_should_push_slideshow_tick`` in main.py), so the TV rotates the resident batch
on its own timer.

This is the gentlest strategy on the TV (one burst of uploads instead of a constant
upload/delete churn), which makes it a useful comparison point when diagnosing crashes.

MVP behaviour: evict-all-refill. On connect it wipes MY-C0002, uploads a fresh batch of
``settings.batch_size`` photos, tracks their ``composite_id -> content_id`` mapping in
memory, and enables the TV's shuffle slideshow. The mapping is not persisted, so a restart
re-uploads the batch (the batch is disposable). Auto-cleanup is skipped in this mode
(``TvCleanupService`` would otherwise delete all but the 3 newest).

"Rotation" throughout this module refers to the slideshow cycling through images, NOT
physical rotation of the TV panel — see ``_enable_tv_rotation`` for the full note.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from framegallery.config import settings
from framegallery.frame_connector.processors.base import ProcessorKind
from framegallery.frame_connector.processors.single_async import SingleAsyncProcessor, logger

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from framegallery.libraries.base import PhotoRef
    from framegallery.libraries.manager import LibraryManager

# The TV category for user-uploaded content; also the rotation category (MY-C000{2}).
_USER_CATEGORY = "MY-C0002"
_ROTATION_CATEGORY = 2

# The TV is sluggish right after a batch of uploads, so give it a moment before
# enabling rotation, then retry the (2s-timeout) calls a few times before giving up.
_ROTATION_SETTLE_SECONDS = 5
_ROTATION_ATTEMPTS = 4
_ROTATION_RETRY_DELAY = 3


class BatchSlideshowProcessor(SingleAsyncProcessor):
    """Upload a batch of images once and let the TV's own slideshow rotate them."""

    kind = ProcessorKind.BATCH_SLIDESHOW

    def __init__(self, ip_address: str, port: int, library_manager: LibraryManager | None = None) -> None:
        super().__init__(ip_address, port, library_manager)
        # In-memory map of composite_id -> TV content_id for the resident batch.
        self._resident: dict[str, str] = {}

    async def open(self) -> None:
        """Connect, refill the batch, and enable the TV's own rotation."""
        await super().open()
        if not self._connected:
            return
        await self._refill_batch()
        await self._enable_tv_rotation()

    async def apply_active_image(self, photo: PhotoRef) -> None:
        """
        Handle an explicit "show this photo now" request.

        The periodic loop does not call this in batch mode (the TV owns rotation),
        so this only runs for explicit user selections: ensure the photo is resident
        (upload if missing) and jump to it.
        """
        if not self._connected or not self._tv_is_online:
            return

        content_id = self._resident.get(photo.composite_id)
        if content_id is None:
            content_id = await self._upload_and_track(photo)
            if content_id is None:
                return

        await self._activate_image(content_id)

    async def _upload_and_track(self, photo: PhotoRef) -> str | None:
        """Upload a photo, record it in the resident map, and return its content_id."""
        photo_bytes = await self._fetch_photo_bytes(photo)
        if photo_bytes is None:
            return None
        data = await self._upload_photo(photo, photo_bytes)
        if not data or not data.get("content_id"):
            logger.error("batch_slideshow: upload of %s returned no content_id", photo.composite_id)
            return None
        content_id = data["content_id"]
        self._resident[photo.composite_id] = content_id
        return content_id

    async def _refill_batch(self) -> None:
        """Evict everything currently on the TV, then upload a fresh batch."""
        if self.library_manager is None:
            logger.error("batch_slideshow: no library_manager; cannot refill batch.")
            return

        # Evict all current user content so we start from a known-empty window.
        existing = await self.list_files(_USER_CATEGORY)
        if existing:
            content_ids = [f["content_id"] for f in existing if f.get("content_id")]
            if content_ids:
                logger.info("batch_slideshow: evicting %d existing images", len(content_ids))
                await self.delete_files(content_ids)
        self._resident.clear()

        # Pick and upload up to batch_size unique photos. pick_photo() is weighted-random
        # and may repeat, so cap the number of attempts to avoid looping forever when the
        # library is smaller than batch_size.
        target = settings.batch_size
        max_attempts = target * 5
        attempts = 0
        while len(self._resident) < target and attempts < max_attempts:
            attempts += 1
            photo = await self.library_manager.pick_photo()
            if photo is None:
                break
            if photo.composite_id in self._resident:
                continue
            await self._upload_and_track(photo)

        logger.info(
            "batch_slideshow: uploaded %d/%d images (%d attempts)",
            len(self._resident),
            target,
            attempts,
        )

    async def _enable_tv_rotation(self) -> None:
        """
        Turn on the TV's built-in shuffle slideshow over the resident batch.

        NOTE ON NAMING: despite the name, ``set_auto_rotation_status`` has nothing to
        do with physically rotating the panel (the motorised auto-rotating wall mount).
        In Samsung's Art Mode API "auto rotation" means *rotating through the images* —
        i.e. the slideshow auto-advancing the displayed artwork every N minutes.
        ``set_auto_rotation_status`` and ``set_slideshow_status`` are two firmware-era
        names for that same slideshow feature (identical payloads: interval in minutes +
        shuffle flag + category). Physical panel orientation is a separate, read-only
        request (``get_current_rotation``) that this app never calls.

        The library's per-request timeout is short (~2s) and the TV is congested
        right after an upload burst, so the enable calls often time out (surfacing
        as an AssertionError inside samsungtvws). We let the TV settle, then retry
        each call a few times, and finally read the status back to confirm.
        """
        minutes = max(1, settings.batch_rotation_minutes)

        # Give the TV a moment to finish digesting the uploads before we ask it to rotate.
        await asyncio.sleep(_ROTATION_SETTLE_SECONDS)

        # Both calls enable the same slideshow via different API names; firmwares differ
        # on which one they honour, so we try both. Success on either is enough.
        auto_ok = await self._enable_rotation_call(
            "set_auto_rotation_status",
            lambda: self._tv.set_auto_rotation_status(duration=minutes, type=True, category=_ROTATION_CATEGORY),
        )
        slideshow_ok = await self._enable_rotation_call(
            "set_slideshow_status",
            lambda: self._tv.set_slideshow_status(duration=minutes, type=True, category=_ROTATION_CATEGORY),
        )

        confirmed = await self._read_rotation_status()
        if confirmed is not None:
            logger.info("batch_slideshow: TV rotation confirmed active: %s", confirmed)
        elif auto_ok or slideshow_ok:
            logger.info(
                "batch_slideshow: rotation enabled (set_auto_rotation_status=%s, set_slideshow_status=%s); "
                "status read-back unavailable",
                auto_ok,
                slideshow_ok,
            )
        else:
            logger.warning(
                "batch_slideshow: could not enable TV rotation after %d attempts; the batch is uploaded "
                "but the TV may not be rotating. It often works on the next run once the TV has settled.",
                _ROTATION_ATTEMPTS,
            )

    async def _enable_rotation_call(self, name: str, call: Callable[[], Awaitable[object]]) -> bool:
        """Invoke a rotation-enable coroutine factory with bounded retries; return success."""
        for attempt in range(1, _ROTATION_ATTEMPTS + 1):
            try:
                await call()
            except Exception as exc:  # noqa: BLE001 -- retry transient TV timeouts (AssertionError etc.)
                logger.debug("batch_slideshow: %s attempt %d/%d failed: %s", name, attempt, _ROTATION_ATTEMPTS, exc)
                if attempt < _ROTATION_ATTEMPTS:
                    await asyncio.sleep(_ROTATION_RETRY_DELAY)
            else:
                return True
        return False

    async def _read_rotation_status(self) -> dict | None:
        """Read the TV's rotation status back (either API), or None if unavailable."""
        for getter in (self._tv.get_auto_rotation_status, self._tv.get_slideshow_status):
            try:
                return await getter()
            except Exception:  # noqa: BLE001, S112 -- diagnostic read-back; fall through to the other getter
                continue
        return None
