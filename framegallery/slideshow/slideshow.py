import logging
logger = logging.getLogger("framegallery")

from blinker import signal

from framegallery.models import Image
from framegallery.repository.image_repository import ImageRepository, NoImagesError


class Slideshow:
    """A class that manages the active image in the slideshow."""

    def __init__(self, image_repository: ImageRepository) -> None:
        self._active_image = None
        self._image_repository = image_repository

    async def update_slideshow(self) -> Image:
        """Update the slideshow with a new image that matches the active filter."""
        image = self._image_repository.get_image_matching_filter(None)

        if image is None:
            raise NoImagesError

        logger.debug("Updating slideshow with image: %s", image.filepath)
        await self.set_slideshow_active_image(image)
        return image

    async def set_slideshow_active_image(self, image: Image) -> None:
        """
        Send a signal that the active image has been updated,
        so that other parts of the system can react to that.
        """
        self._active_image = image
        active_image_updated = signal("active_image_updated")
        await active_image_updated.send_async(self, active_image=self._active_image)

        logger.info("Active image: %s", self._active_image.filepath)
