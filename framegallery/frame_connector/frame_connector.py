"""
The FrameConnector provides a signal handler for the `active_image_updated` signal, and will
update the active image on the Frame TV when the signal is emitted.
"""

import asyncio
import os
from pathlib import Path

import websockets
from blinker import signal
from samsungtvws.async_art import SamsungTVAsyncArt

from framegallery.config import settings
from framegallery.logging_config import setup_logging
from framegallery.models import Image

api_version = "4.3.4.0"
logger = setup_logging(log_level=settings.log_level)


class TvNotConnectedError(Exception):
    """Exception raised when the TV is not connected."""

class TvConnectionTimeoutError(TvNotConnectedError):
    """Exception raised when the TV connection times out."""


class FrameConnector:
    """A class that connects to the Frame TV and updates the active image on the TV."""

    IDEAL_ASPECT_RATIO_HEIGHT = 9
    IDEAL_ASPECT_RATIO_WIDTH = 16

    def __init__(self, ip_address: str, port: int) -> None:
        self._tv = None
        self._ip_address = ip_address
        self._port = port
        self._pid = os.getpid()
        self._token_file = (
            Path(__file__).parent / f"tv-token-{self._pid}.txt"
        )
        self._background_tasks = set()

        self._latest_content_id = None
        self._tv_is_online = False
        self._connected = False

        self._active_image_updated_signal = signal("active_image_updated")

        # Check if the TV is available on the network. If it is, the connection sequence will be started.
        self._start_reconnection_pinger()

    async def open(self) -> None:
        """Open a connection to the TV and start listening to the slideshow update events."""
        if not self._tv_is_online:
            return

        try:
            await self._tv.on()
            await self._tv.start_listening()

            self._tv.set_callback(trigger="go_to_standby", callback=self.go_to_standby)
        except TimeoutError as e:
            logger.exception("Timeout error connecting to TV.")
            raise TvConnectionTimeoutError from e

        self._connected = True
        self._active_image_updated_signal.connect(self._on_active_image_updated)

    async def close(self) -> None:
        """Close the connection to the TV, and (re)start the reconnection pinger."""
        await self._tv.close()
        self._connected = False
        self._active_image_updated_signal.disconnect(self._on_active_image_updated)
        self._start_reconnection_pinger()

    def _start_reconnection_pinger(self) -> None:
        """Start the reconnection timer."""
        logger.info("Starting reconnection timer")
        pinger = asyncio.create_task(self._reconnect_ping())
        self._background_tasks.add(pinger)
        pinger.add_done_callback(self._background_tasks.discard)


    async def _reconnect_ping(self) -> None:
        """Ping the TV to check if it is online."""
        from icmplib import ping

        while True:
            try:
                response = ping(self._ip_address, count=1, timeout=2, privileged=False)
                if not response.is_alive:
                    logger.debug(
                        "Ping to %s failed, retrying in 10 seconds", self._ip_address
                    )
                    self._tv_is_online = False
                else:
                    logger.info(
                        "Ping to %s successful, reconnecting to the TV.", self._ip_address
                    )
                    self._tv_is_online = True
                    await self.reconnect()
                    break

            except Exception:
                logger.exception("Error during ping.")
            await asyncio.sleep(10)

    async def reconnect(self) -> None:
        """Reconnect to the TV."""
        self._tv = SamsungTVAsyncArt(
            host=self._ip_address,
            port=self._port,
            name=f"FrameTV-{self._pid}",
            token_file=self._token_file,
        )
        await self.open()

    async def get_active_item_details(self) -> dict|None:
        """Get the current active item details from the TV."""
        if not self._connected or not self._tv_is_online:
            return None

        data = await self._tv.get_current()
        logger.critical("Current active item: %s", data)

        return data

    async def _on_active_image_updated(self, _: object, active_image: Image) -> None:
        logger.info("Updating active image on TV: %s", active_image.filepath)

        # Upload the image to the TV
        try:
            if not self._connected or not self._tv_is_online:
                return

            if not self._tv.art_mode:
                logger.debug("TV is not in art-mode, skipping image update.")
                return

            logger.debug("_on_active_image_updated: TV connected, uploading image")
            data = await self._upload_image(active_image)
        except websockets.exceptions.ConnectionClosedError:
            logger.exception(
                "Connection to TV is closed, perhaps the TV is off?"
            )
            await self.close()
            return
        except AssertionError:
            logger.exception("Upload failed, retrying after reconnecting")
            try:
                await self.reconnect()
            except TvNotConnectedError:
                logger.exception("TV not connected, cannot update active image.")
                return
            return
        except Exception:
            # log as much info about the error as possible

            import traceback

            logger.exception(
                "Error uploading image to TV, traceback: %s", traceback.format_exc()
            )
            await self.close()
            return

        # Make uploaded image active
        await self._activate_image(data["content_id"])

        # Delete previously active image
        if self._latest_content_id is not None:
            await self._delete_image(self._latest_content_id)

        self._latest_content_id = data["content_id"]

    async def _upload_image(self, image: Image) -> dict|None:
        """Upload image to TV and return the uploaded file details as provided by the television."""
        logger.info("Uploading image %s to TV", image.filepath)

        file_data, file_type = self._read_file(image.filepath)

        matte = "none" if (image.aspect_width == self.IDEAL_ASPECT_RATIO_WIDTH
                           and image.aspect_height == self.IDEAL_ASPECT_RATIO_HEIGHT) \
            else "shadowbox_black"

        logger.info(
            "Going to upload %s with file_type %s and filesize: %d",
            image.filepath,
            file_type,
            len(file_data),
        )
        data = await self._tv.upload(
            file_data,
            file_type=file_type,
            timeout=60,
            matte=matte,
            portrait_matte="none",
        )

        logger.info("Received uploaded data details: %s", data)

        if not data:
            logger.error("Upload failed, lets retry after reconnecting.")
            try:
                await self.open()
            except TvNotConnectedError:
                logger.exception("TV not connected, cannot update active image.")
                return None
            return None

        return data

    @staticmethod
    def _read_file(image_path: str) -> tuple[bytes, str]|tuple[None, None]:
        """Read image file, return file binary data and file type."""
        try:
            with Path(image_path).open("rb") as f:
                file_data = f.read()
                file_type = FrameConnector._get_file_type(image_path)
                return file_data, file_type
        except Exception:
            logger.exception("Error reading file: %s", image_path)
            raise

    @staticmethod
    def _get_file_type(image_path: str) -> str:
        """Try to figure out what kind of image file is, starting with the extension."""
        try:
            file_type = Path(image_path).suffix
            return file_type.lower() if file_type else None
        except Exception:
            logger.exception("Error reading file: %s", image_path)
            raise

    async def _activate_image(self, content_id: str) -> None:
        logger.info("Activating image %s",  content_id)
        await self._tv.select_image(content_id, "MY-C0002")

    async def _delete_image(self, content_id: str) -> None:
        await self._tv.delete(content_id)

    async def tv_keepalive(self) -> None:
        """Keep WebSocket connection alive."""
        while True:
            if not self._tv.connection:
                logger.warning("Should be reconnecting to TV")
            else:
                logger.warning("No need to reconnect to TV")
            await asyncio.sleep(10)  # Adjust interval as needed

    async def go_to_standby(self) -> None:
        """Close the connector when the TV goes to standby."""
        logger.info("TV is going to standby")
        await self.close()
