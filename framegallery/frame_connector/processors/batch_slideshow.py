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
memory, and enables the TV's shuffle rotation. The mapping is not persisted, so a restart
re-uploads the batch (the batch is disposable). Auto-cleanup is skipped in this mode
(``TvCleanupService`` would otherwise delete all but the 3 newest).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from framegallery.config import settings
from framegallery.frame_connector.processors.base import ProcessorKind
from framegallery.frame_connector.processors.single_async import SingleAsyncProcessor, logger

if TYPE_CHECKING:
    from framegallery.libraries.base import PhotoRef
    from framegallery.libraries.manager import LibraryManager

# The TV category for user-uploaded content; also the rotation category (MY-C000{2}).
_USER_CATEGORY = "MY-C0002"
_ROTATION_CATEGORY = 2


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
        """Turn on the TV's built-in shuffle rotation over the resident batch."""
        minutes = max(1, settings.batch_rotation_minutes)
        # Both calls are best-effort: firmwares differ on which rotation API they
        # honour, so we try both and don't let a rejection abort the batch.
        try:
            await self._tv.set_auto_rotation_status(duration=minutes, type=True, category=_ROTATION_CATEGORY)
        except Exception:  # noqa: BLE001 -- best-effort; log and continue
            logger.exception("batch_slideshow: set_auto_rotation_status failed")
        try:
            await self._tv.set_slideshow_status(duration=minutes, type=True, category=_ROTATION_CATEGORY)
        except Exception:  # noqa: BLE001 -- best-effort; log and continue
            logger.exception("batch_slideshow: set_slideshow_status failed")

        # Read the state back so the logs show what the firmware actually accepted.
        try:
            status = await self._tv.get_auto_rotation_status()
            logger.info("batch_slideshow: auto-rotation status now: %s", status)
        except Exception:  # noqa: BLE001 -- diagnostic read-back only
            logger.debug("batch_slideshow: could not read back auto-rotation status")
