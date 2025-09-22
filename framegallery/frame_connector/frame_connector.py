"""
The FrameConnector provides a signal handler for the `active_image_updated` signal, and will
update the active image on the Frame TV when the signal is emitted.
"""

import asyncio
import json
import os
import traceback
import uuid
from pathlib import Path

import websockets
from blinker import signal
from icmplib import ping
from samsungtvws.async_art import ArtChannelEmitCommand, SamsungTVAsyncArt

from framegallery.aspect_ratio import get_aspect_ratio
from framegallery.config import settings
from framegallery.image_manipulation import get_cropped_image_dimensions, read_file_data
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
        self._tv: SamsungTVAsyncArt | None = None
        self._ip_address = ip_address
        self._port = port
        self._pid = os.getpid()
        self._token_file = Path(__file__).parent / f"tv-token-{self._pid}.txt"
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
        while True:
            try:
                response = ping(self._ip_address, count=1, timeout=2, privileged=False)
                if not response.is_alive:
                    logger.debug("Ping to %s failed, retrying in 10 seconds", self._ip_address)
                    self._tv_is_online = False
                else:
                    logger.info("Ping to %s successful, reconnecting to the TV.", self._ip_address)
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

    async def get_active_item_details(self) -> dict | None:
        """Get the current active item details from the TV."""
        if not self._connected or not self._tv_is_online:
            return None

        data = await self._tv.get_current()
        logger.critical("Current active item: %s", data)

        return data

    async def _on_active_image_updated(self, _: object, active_image: Image) -> None:
        logger.info("Updating active image on TV (via slideshow signal): %s", active_image.filepath)

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
            logger.exception("Connection to TV is closed, perhaps the TV is off?")
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

            logger.exception("Error uploading image to TV, traceback: %s", traceback.format_exc())
            await self.close()
            return

        # Make uploaded image active
        if data and data.get("content_id"):
            await self._activate_image(data["content_id"])
            # Delete previously active image
            if self._latest_content_id is not None:
                await self._delete_image(self._latest_content_id)
            self._latest_content_id = data["content_id"]
        elif data:
            logger.error("Slideshow image upload completed but did not return a content_id.")
        else:
            logger.error("Slideshow image upload failed, data is None.")

    async def activate_image(self, image: Image) -> None:
        """Activate an image on the Frame TV, uploading if necessary."""
        logger.info("Activating image: %s via explicit request.", image.filepath)

        # Check connection status first
        if not self._connected or not self._tv_is_online:
            logger.error("TV not connected, cannot activate image.")
            return

        # Always upload the image (potentially cropped) to get the latest content_id
        logger.info("Uploading image %s to ensure it's available...", image.filepath)

        uploaded_data = await self._upload_image(image)
        if not uploaded_data:
            logger.error("Upload failed for image %s", image.filepath)
            return

        content_id = uploaded_data.get("content_id")

        if content_id:
            logger.info("Upload successful (content_id: %s), activating image...", content_id)
            await self._activate_image(content_id)
        else:
            logger.error("Upload completed but did not return a content_id.")

    async def _upload_image(self, image: Image) -> dict | None:
        """Upload image to TV and return the uploaded file details as provided by the television."""
        logger.info("Uploading image %s to TV", image.filepath)

        file_data, file_type = read_file_data(image)
        if file_type is None:
            logger.error("File type not determined for image %s, canceling file upload", image.filepath)
            return None

        cropped_width, cropped_height = get_cropped_image_dimensions(image)
        cropped_width_aspect_width, cropped_width_aspect_height = get_aspect_ratio(cropped_width, cropped_height)

        logger.info("Cropped image dimensions: %s:%s", cropped_width, cropped_height)
        logger.info("Cropped image aspect ratio: %s:%s", cropped_width_aspect_width, cropped_width_aspect_height)

        matte = (
            "none"
            if (
                cropped_width_aspect_width == self.IDEAL_ASPECT_RATIO_WIDTH
                and cropped_width_aspect_height == self.IDEAL_ASPECT_RATIO_HEIGHT
            )
            else "shadowbox_black"
        )

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

    async def _activate_image(self, content_id: str) -> None:
        logger.info("Activating image %s", content_id)
        await self._tv.select_image(content_id, "MY-C0002")

    async def _delete_image(self, content_id: str) -> None:
        logger.info("Deleting image %s", content_id)
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

    def _transform_file_data(self, file_data: dict) -> dict:
        """Transform TV file data into standardized format."""
        # Extract content ID for display name
        content_id = file_data.get("content_id", "Unknown")

        # Generate file_name from content_id (e.g., "MY_F33145" -> "MY_F33145")
        file_name = content_id

        # Determine file type from content_type and other indicators
        content_type = file_data.get("content_type", "mobile")
        # Default to JPEG for mobile uploads, Samsung Art for preinstalled content
        file_type = "SAMSUNG_ART" if content_type == "preinstall" else "JPEG"

        file_info = {
            "content_id": content_id,
            "category_id": file_data.get("category_id"),
            "file_name": file_name,
            "file_type": file_type,
            "file_size": file_data.get("file_size"),
            "date": file_data.get("image_date"),
            "thumbnail_available": True,  # Frame TV typically has thumbnails for all images
            "matte": file_data.get("matte_id"),
        }

        # Include any additional metadata fields from the TV
        for key, value in file_data.items():
            if key not in file_info:
                file_info[key] = value

        return file_info

    def _filter_files_by_category(self, files: list[dict], category: str | None) -> list[dict]:
        """Filter files by category and transform them."""
        return [
            self._transform_file_data(file_data)
            for file_data in files
            if file_data.get("category_id") == category or category is None
        ]

    async def _get_available_files_with_timeout(
        self, category: str | None = None, timeout_seconds: int = 10
    ) -> list[dict] | None:
        """
        Get available files from TV with a configurable timeout.

        The Samsung TV library has a hardcoded 2-second timeout which is often too short
        for TVs that take longer to respond. This method implements a longer timeout.

        Args:
            category: The image folder/category on the TV
            timeout_seconds: Timeout in seconds (default: 10)

        Returns:
            List of available files or None if timeout/error occurs

        """
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        request_data = {"request": "get_content_list", "category": category, "id": request_id, "request_id": request_id}

        # Set up the pending request future
        self._tv.pending_requests[request_id] = asyncio.Future()

        try:
            # Send the request
            await self._tv.send_command(ArtChannelEmitCommand.art_app_request(request_data))

            # Wait for response with extended timeout
            response = await asyncio.wait_for(self._tv.pending_requests[request_id], timeout_seconds)
            data = json.loads(response["data"])

            # Clean up pending request
            self._tv.pending_requests.pop(request_id, None)

            if data and data.get("event", "*") == "error":
                logger.error("TV returned error for get_content_list: %s", data.get("error_code"))
                return None

            if not data or not data.get("content_list"):
                logger.info("No content list returned from TV")
                return []

            # Parse and filter by category if specified
            content_list = json.loads(data["content_list"])
            return [v for v in content_list if v.get("category_id") == category] if category else content_list

        except TimeoutError:
            logger.warning("Timeout waiting for TV response after %d seconds", timeout_seconds)
            self._tv.pending_requests.pop(request_id, None)
            return None
        except Exception:
            logger.exception("Error getting available files with extended timeout")
            self._tv.pending_requests.pop(request_id, None)
            return None

    async def list_files(self, category: str = "MY-C0002") -> list[dict] | None:
        """
        List all files available on the Samsung Frame TV.

        Args:
            category: The image folder/category on the TV (default: "MY-C0002")
                     Common categories:
                     - "MY-C0002": User uploaded content (default)
                     - "MY-C0001": Samsung Art Store content
                     - "MY-C000X": Other categories following the pattern

        Returns:
            List of dictionaries containing file information from the TV,
            or None if the TV is not connected or an error occurs.

        """
        # Check connection status
        if not self._connected or not self._tv_is_online:
            logger.error("TV not connected, cannot list files.")
            return None

        try:
            # Call Samsung TV API to get available files with extended timeout
            logger.info("Retrieving file list from TV for category: %s", category)
            available_files = await self._get_available_files_with_timeout(category)

            if not available_files:
                logger.warning("No files returned from TV")
                return []

            # Parse and filter the response
            file_list = self._filter_files_by_category(available_files, category)
            logger.info("Retrieved %d files from TV for category %s", len(file_list), category)

        except websockets.exceptions.ConnectionClosedError:
            logger.exception("Connection to TV is closed, perhaps the TV is off?")
            await self.close()
            return None
        except TimeoutError:
            logger.exception("Timeout while retrieving file list from TV")
            raise TvConnectionTimeoutError from None
        except Exception:
            logger.exception("Error retrieving file list from TV")
            return None
        else:
            return file_list

    async def delete_file(self, content_id: str) -> bool | None:
        """
        Delete a file from the Samsung Frame TV.

        Args:
            content_id: The content ID of the file to delete (e.g., "MY-F0001")

        Returns:
            True if file was successfully deleted
            False if file was not found or could not be deleted
            None if TV is not connected or unavailable

        Raises:
            TvConnectionTimeoutError: If the TV connection times out

        """
        if not self._connected or not self._tv_is_online:
            logger.error("TV not connected, cannot delete file.")
            return None

        try:
            logger.info("Deleting file from TV: %s", content_id)

            # Use the Samsung TV library's built-in delete method
            await self._tv.delete(content_id)

        except websockets.exceptions.ConnectionClosedError:
            logger.exception("Connection to TV is closed, perhaps the TV is off?")
            await self.close()
            return None
        except TimeoutError:
            logger.exception("Timeout while deleting file from TV")
            raise TvConnectionTimeoutError from None
        except Exception as e:
            logger.exception("Error deleting file from TV")
            # If the error indicates the file wasn't found, return False
            # Otherwise, return None to indicate a connection/system error
            error_msg = str(e).lower()
            if any(term in error_msg for term in ["not found", "does not exist", "invalid"]):
                logger.warning("File %s not found on TV", content_id)
                return False
            return None
        else:
            logger.info("Successfully deleted file from TV: %s", content_id)
            return True

    async def delete_files(self, content_ids: list[str]) -> dict[str, bool] | None:
        """
        Delete multiple files from the Samsung Frame TV.

        Args:
            content_ids: List of content IDs to delete (e.g., ["MY-F0001", "MY-F0002"])

        Returns:
            Dictionary mapping content_id to success status (True/False) if TV is connected
            None if TV is not connected or unavailable

        Raises:
            TvConnectionTimeoutError: If the TV connection times out

        """
        if not self._connected or not self._tv_is_online:
            logger.error("TV not connected, cannot delete files.")
            return None

        if not content_ids:
            logger.info("No files to delete")
            return {}

        try:
            logger.info("Deleting %d files from TV: %s", len(content_ids), content_ids)

            # Chunk the content_ids into batches of max 20 files to avoid WebSocket API errors
            chunk_size = 20
            result = {}

            for i in range(0, len(content_ids), chunk_size):
                chunk = content_ids[i : i + chunk_size]
                logger.info("Deleting chunk %d-%d: %d files", i + 1, min(i + chunk_size, len(content_ids)), len(chunk))

                # Use the Samsung TV library's built-in delete_list method
                await self._tv.delete_list(chunk)

                # The delete_list method doesn't return individual status, so we assume all succeeded
                # In practice, if any fail, the method would raise an exception
                chunk_result = dict.fromkeys(chunk, True)
                result.update(chunk_result)

                # Small delay between chunks to avoid overwhelming the TV
                if i + chunk_size < len(content_ids):
                    await asyncio.sleep(0.1)

            num_chunks = (len(content_ids) + chunk_size - 1) // chunk_size
            logger.info("Successfully deleted %d files from TV in %d chunks", len(content_ids), num_chunks)

        except websockets.exceptions.ConnectionClosedError:
            logger.exception("Connection to TV is closed, perhaps the TV is off?")
            await self.close()
            return None
        except TimeoutError:
            logger.exception("Timeout while deleting files from TV")
            raise TvConnectionTimeoutError from None
        except Exception as e:
            logger.exception("Error deleting files from TV")
            # If the error indicates files weren't found, return False for all
            # Otherwise, return None to indicate a connection/system error
            error_msg = str(e).lower()
            if any(term in error_msg for term in ["not found", "does not exist", "invalid"]):
                logger.warning("Some files not found on TV: %s", content_ids)
                return dict.fromkeys(content_ids, False)
            return None
        else:
            return result
