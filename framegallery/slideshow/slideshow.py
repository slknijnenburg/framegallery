import logging

from blinker import signal

from framegallery.libraries.base import PhotoRef
from framegallery.libraries.manager import LibraryManager

logger = logging.getLogger("framegallery")


class Slideshow:
    """Manages the active photo in the slideshow, sourced from any enabled library."""

    def __init__(self, library_manager: LibraryManager) -> None:
        self._active_photo: PhotoRef | None = None
        self._library_manager = library_manager

    async def update_slideshow(self) -> PhotoRef | None:
        """Pick a new photo across enabled libraries and make it the active image."""
        photo = await self._library_manager.pick_photo()

        if photo is None:
            logger.warning("No photo available for slideshow update")
            return None

        logger.debug("Updating slideshow with photo: %s", photo.composite_id)
        await self.set_slideshow_active_image(photo)
        return photo

    async def set_slideshow_active_image(self, photo: PhotoRef) -> None:
        """
        Send a signal that the active photo has been updated,
        so that other parts of the system can react to that.
        """
        self._active_photo = photo
        active_image_updated = signal("active_image_updated")
        await active_image_updated.send_async(self, active_photo=photo)

        logger.info("Active photo: %s", photo.composite_id)
