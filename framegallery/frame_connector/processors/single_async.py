"""
The ``single_async`` upload processor.

This is the original FrameGallery behaviour: a persistent async ``SamsungTVAsyncArt``
WebSocket that, on each ``active_image_updated`` signal, uploads one image, activates
it (``select_image``), and deletes the previously-active image.
"""

from __future__ import annotations

import asyncio
import json
import traceback
import uuid
from typing import TYPE_CHECKING

import websockets
from samsungtvws.async_art import ArtChannelEmitCommand, SamsungTVAsyncArt

from framegallery.config import settings
from framegallery.frame_connector.processors.base import (
    ProcessorKind,
    TvConnectionTimeoutError,
    TvNotConnectedError,
    UploadProcessor,
)
from framegallery.logging_config import setup_logging

if TYPE_CHECKING:
    from framegallery.libraries.base import PhotoBytes, PhotoRef
    from framegallery.libraries.manager import LibraryManager

logger = setup_logging(
    log_level=settings.log_level,
    websocket_log_level=settings.websocket_log_level,
    logs_path=settings.logs_path,
)


class SingleAsyncProcessor(UploadProcessor):
    """Push one active image at a time over a persistent async WebSocket."""

    kind = ProcessorKind.SINGLE_ASYNC

    def __init__(self, ip_address: str, port: int, library_manager: LibraryManager | None = None) -> None:
        super().__init__(ip_address, port, library_manager)
        self._tv: SamsungTVAsyncArt | None = None

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
        self._on_active_image_signal_connect()

    async def close(self) -> None:
        """Close the connection to the TV, and (re)start the reconnection pinger."""
        if self._tv is not None:
            await self._tv.close()
        self._connected = False
        self._on_active_image_signal_disconnect()
        self._start_reconnection_pinger()

    async def reconnect(self) -> None:
        """Reconnect to the TV."""
        await self._ensure_token()
        self._tv = SamsungTVAsyncArt(
            host=self._ip_address,
            port=self._port,
            name=settings.tv_client_name,
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

    async def _is_art_mode_active(self) -> bool:
        """
        Return whether the TV is currently in art mode.

        The cached `self._tv.art_mode` flag is only updated from push events
        (e.g. `art_mode_changed`), so it can be stale when the app connected
        while the TV was already in art mode, or when a transition event was
        missed. Query the live status and fall back to the cached flag only if
        the query fails.
        """
        try:
            return await self._tv.get_artmode() == "on"
        except (AssertionError, KeyError, OSError, websockets.exceptions.WebSocketException):
            logger.debug(
                "Live art-mode query failed; falling back to cached art_mode=%s",
                self._tv.art_mode,
            )
            return bool(self._tv.art_mode)

    async def apply_active_image(self, photo: PhotoRef) -> None:  # noqa: PLR0911, C901
        """Upload the given photo to the TV, activate it, and delete the previous one."""
        logger.info("Updating active image on TV (via slideshow signal): %s", photo.composite_id)

        # Upload the image to the TV
        try:
            if not self._connected or not self._tv_is_online:
                return

            if not await self._is_art_mode_active():
                logger.debug("TV is not in art-mode, skipping image update.")
                return

            logger.debug("apply_active_image: TV connected, uploading image")
            photo_bytes = await self._fetch_photo_bytes(photo)
            if photo_bytes is None:
                return
            data = await self._upload_photo(photo, photo_bytes)
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

        # Make uploaded image active. Give the TV a moment to finish processing the
        # upload before switching to it: activating too soon can crash Art Mode.
        if data and data.get("content_id"):
            await self._settle()
            await self._activate_image(data["content_id"])
            # Delete previously active image
            if self._latest_content_id is not None:
                await self._settle()
                await self._delete_image(self._latest_content_id)
            self._latest_content_id = data["content_id"]
        elif data:
            logger.error("Slideshow image upload completed but did not return a content_id.")
        else:
            logger.error("Slideshow image upload failed, data is None.")

    async def _upload_photo(self, photo: PhotoRef, photo_bytes: PhotoBytes) -> dict | None:
        """Upload photo bytes to TV and return the uploaded file details as provided by the television."""
        logger.info("Uploading photo %s to TV", photo.composite_id)

        file_data = photo_bytes.data
        file_type = photo_bytes.file_type_suffix
        matte = self._compute_matte(photo_bytes)

        logger.info(
            "Going to upload %s with file_type %s and filesize: %d",
            photo.composite_id,
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

    async def go_to_standby(self) -> None:
        """Close the connector when the TV goes to standby."""
        logger.info("TV is going to standby")
        await self.close()

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
