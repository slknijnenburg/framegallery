import logging

from blinker import signal

from sqlalchemy.orm import Session

from framegallery.crud import get_random_image
from framegallery.models import Image


class Slideshow:
    def __init__(self, db: Session):
        self._active_image = None
        self._db = db

    async def update_slideshow(self) -> Image:
        image = get_random_image(self._db)
        if image is None:
            raise ValueError('No images in database')

        self._active_image = image
        active_image_updated = signal('active_image_updated')
        await active_image_updated.send_async(self, active_image=self._active_image)

        logging.info(f"Active image: {self._active_image.filepath}")

        return self._active_image