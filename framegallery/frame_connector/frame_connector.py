"""
The FrameConnector provides a signal handler for the `active_image_updated` signal, and will
update the active image on the Frame TV when the signal is emitted.
"""
import logging
import os
from typing import Tuple

from blinker import signal
from samsungtvws.async_art import SamsungTVAsyncArt

from framegallery.models import Image


class FrameConnector:
    def __init__(self, tv: SamsungTVAsyncArt):
        self._tv = tv
        self._latest_content_id = None

        active_image_updated = signal('active_image_updated')
        active_image_updated.connect(self._on_active_image_updated)

    async def _on_active_image_updated(self, sender, active_image: Image):
        logging.info(f"Updating active image on TV: {active_image.filepath}")


        # Upload the image to the TV
        data = await self._upload_image(active_image)
        # Make uploaded image active
        await self._activate_image(data['content_id'])

        # Delete previously active image
        if self._latest_content_id is not None:
            await self._delete_image(self._latest_content_id)

        self._latest_content_id = data['content_id']


    async def _upload_image(self, image: Image):
        logging.info(f"Uploading image {image.filepath} to TV")
        # await self._tv.upload(image.filepath, file_type=image.filetype, matte=image.matte_id)

        file_data, file_type = self._read_file(image.filepath)

        logging.info('Going to upload {} with file_type {}'.format(image.filepath, file_type))
        data = await self._tv.upload(file_data, file_type=file_type, timeout=60, matte="none", portrait_matte="none")

        logging.info('Received uploaded data details: {}'.format(data))

        return data

    """
    read image file, return file binary data and file type
    """
    @staticmethod
    def _read_file(image_path: str) -> Tuple[bytes, str]:
        try:
            with open(image_path, 'rb') as f:
                file_data = f.read()
            file_type = FrameConnector._get_file_type(image_path)
            return file_data, file_type
        except Exception as e:
            logging.error('Error reading file: {}, {}'.format(image_path, e))
            raise e

    '''
    Try to figure out what kind of image file is, starting with the extension
    '''
    @staticmethod
    def _get_file_type(image_path) -> str:
        try:
            file_type = os.path.splitext(image_path)[1][1:].lower()
            file_type = file_type.lower() if file_type else None
            return file_type
        except Exception as e:
            logging.error('Error reading file: {}, {}'.format(image_path, e))
            raise e

    async def _activate_image(self, content_id: str):
        logging.info(f"Activating image {content_id}")
        await self._tv.select_image(content_id, "MY-C0002")

    async def _delete_image(self, content_id: str):
        await self._tv.delete(content_id)