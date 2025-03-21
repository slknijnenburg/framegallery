import logging

from blinker import signal

from framegallery.models import Image
from framegallery.repository.config_repository import ConfigRepository
from framegallery.repository.image_repository import ImageRepository


class Slideshow:
    def __init__(self, image_repository: ImageRepository):
        self._active_image = None
        self._image_repository = image_repository

    async def update_slideshow(self) -> Image:
        image = self._image_repository.get_image_matching_filter(None)

        if image is None:
            raise ValueError("No images in database")

        await self.set_slideshow_active_image(image)
        return image

    async def set_slideshow_active_image(self, image: Image) -> None:
        self._active_image = image
        active_image_updated = signal("active_image_updated")
        await active_image_updated.send_async(self, active_image=self._active_image)

        logging.info(f"Active image: {self._active_image.filepath}")


def get_slideshow(image_repository: ImageRepository):
    yield Slideshow(image_repository)
