import datetime
import logging

from blinker import signal

from framegallery.models import Image
from framegallery.repository.config_repository import ConfigKey, ConfigRepository

logger = logging.getLogger("framegallery")

class UpdateCurrentActiveImageConfigListener:
    """Update the current active image configuration when the active image changes."""

    def __init__(self, config_repository: ConfigRepository) -> None:
        self._config_repository = config_repository
        self._active_image_updated_signal = signal("active_image_updated")
        self._active_image_updated_signal.connect(self._on_active_image_updated)

    async def _on_active_image_updated(self, _: object, active_image: Image) -> None:
        """Update the current active image configuration in the database."""
        logger.debug("Updating current active image in config to %s", active_image.id)
        self._config_repository.set(ConfigKey.CURRENT_ACTIVE_IMAGE, active_image.id)
        self._config_repository.set(
            ConfigKey.CURRENT_ACTIVE_IMAGE_SINCE, datetime.datetime.now(tz=datetime.UTC).isoformat()
        )
