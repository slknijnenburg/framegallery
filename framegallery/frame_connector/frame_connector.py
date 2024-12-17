"""
The FrameConnector provides a signal handler for the `active_image_updated` signal, and will
update the active image on the Frame TV when the signal is emitted.
"""
import asyncio
import logging
import os
from typing import Tuple

import websockets
from blinker import signal
from samsungtvws.async_art import SamsungTVAsyncArt

from framegallery.models import Image

api_version = "4.3.4.0"

class TvNotConnectedError(Exception):
    """Exception raised when the TV is not connected."""
    pass


class FrameConnector:
    def __init__(self, ip_address: str, port: int):
        self._tv = None
        self._ip_address = ip_address
        self._port = port
        self._pid = os.getpid()
        self._token_file = os.path.dirname(os.path.realpath(__file__)) + f"/tv-token-{self._pid}.txt"

        self._latest_content_id = None
        self._tv_is_online = False
        self._connected = False

        self._active_image_updated_signal = signal('active_image_updated')
        
        # Check if the TV is available on the network. If it is, the connection sequence will be started.
        self._start_reconnection_pinger()

    async def open(self):
        if not self._tv_is_online:
            return

        try:
            await self._tv.on()
            await self._tv.start_listening()

            self._tv.set_callback(trigger='go_to_standby', callback=self.go_to_standby)
        except TimeoutError as e:
            logging.error(f"Timeout error connecting to TV: {e}")
            raise TvNotConnectedError("Timeout error connecting to TV", e)

        self._connected = True
        self._active_image_updated_signal.connect(self._on_active_image_updated)

    async def close(self):
        await self._tv.close()
        self._connected = False
        self._active_image_updated_signal.disconnect(self._on_active_image_updated)
        self._start_reconnection_pinger()

    def _start_reconnection_pinger(self):
        logging.info("Starting reconnection timer")
        asyncio.create_task(self._reconnect_ping())

    async def _reconnect_ping(self):
        from icmplib import ping

        while True:
            try:
                response = ping(self._ip_address, count=1, timeout=2)
                if not response.is_alive:
                    logging.debug(f"Ping to {self._ip_address} failed, retrying in 10 seconds")
                    self._tv_is_online = False
                else:
                    logging.info(f"Ping to {self._ip_address} successful, reconnecting to the TV")
                    self._tv_is_online = True
                    await self.reconnect()
                    break

            except Exception as e:
                logging.error(f"Error during ping: {e}")
            await asyncio.sleep(10)


    async def reconnect(self):
        self._tv = SamsungTVAsyncArt(host=self._ip_address, port=self._port, name=f"FrameTV-{self._pid}", token_file=self._token_file)
        await self.open()

    async def get_active_item_details(self):
        if not self._connected or not self._tv_is_online:
            return

        data = await self._tv.get_current()
        logging.critical(f"Current active item: {data}")

        return data

    async def _on_active_image_updated(self, sender, active_image: Image):
        logging.info(f"Updating active image on TV: {active_image.filepath}")

        # Upload the image to the TV
        try:
            if not self._connected or not self._tv_is_online:
                    return

            logging.debug("_on_active_image_updated: TV connected, uploading image")
            data = await self._upload_image(active_image)
        except websockets.exceptions.ConnectionClosedError as e:
            logging.error(f"Connection to TV is closed, perhaps the TV is off? Error: {e}")
            await self.close()
            return
        except AssertionError:
            logging.error("Upload failed, retrying after reconnecting")
            try:
                await self.reconnect()
            except TvNotConnectedError as e:
                logging.error(f"TV not connected, cannot update active image: {e}")
                return
            return
        except Exception as e:
            # log as much info about the error as possible

            import traceback
            logging.error(f"Error uploading image to TV: {e} with traceback {traceback.format_exc()}")
            await self.close()
            return

        assert data

        # Make uploaded image active
        await self._activate_image(data['content_id'])

        # Delete previously active image
        if self._latest_content_id is not None:
            await self._delete_image(self._latest_content_id)

        self._latest_content_id = data['content_id']

    async def _upload_image(self, image: Image):
        logging.info(f"Uploading image {image.filepath} to TV")

        file_data, file_type = self._read_file(image.filepath)

        if image.aspect_width == 16 and image.aspect_height == 9:
            matte="none"
        else:
            matte = "shadowbox_black"

        logging.info('Going to upload {} with file_type {} and filesize: {}'.format(image.filepath, file_type, len(file_data)))
        data = await self._tv.upload(file_data, file_type=file_type, timeout=60, matte=matte, portrait_matte="none")

        logging.info('Received uploaded data details: {}'.format(data))

        if not data:
            logging.error('Upload failed, lets retry after reconnecting.')
            try:
                await self.open()
            except TvNotConnectedError as e:
                logging.error(f"TV not connected, cannot update active image: {e}")
                return None
            return None

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

    # Background task to start and keep WebSocket connection alive
    async def tv_keepalive(self):
        while True:
            if not self._tv.connection:
                logging.warning("Should be reconnecting to TV")
            else:
                logging.warning("No need to reconnect to TV")
            await asyncio.sleep(10)  # Adjust interval as needed

    async def go_to_standby(self, trigger, data):
        logging.info("TV is going going to standby")
        await self.close()