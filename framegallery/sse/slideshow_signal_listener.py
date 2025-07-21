import asyncio
import logging

from blinker import signal

from framegallery.models import Image

logger = logging.getLogger("framegallery")


class SlideshowSignalSSEListener:
    """Listens for slideshow signals and puts events onto an SSE queue."""

    def __init__(self, event_queue: asyncio.Queue) -> None:
        self._event_queue = event_queue
        self._active_image_updated_signal = signal("active_image_updated")
        self._active_image_updated_signal.connect(self._on_active_image_updated)

    async def _on_active_image_updated(self, _: object, active_image: Image) -> None:
        """Handle the active_image_updated signal and put event onto the SSE queue."""
        if self._event_queue:
            event_data = {"event": "slideshow_update", "imageId": active_image.id}
            await self._event_queue.put(event_data)
            logger.info(
                "SlideshowSignalSSEListener: Put event on queue: %s", event_data
            )
