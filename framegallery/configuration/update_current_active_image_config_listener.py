import datetime

from blinker import signal

from framegallery.models import Image
from framegallery.repository.config_repository import ConfigKey, ConfigRepository


class UpdateCurrentActiveImageConfigListener:
    """Update the current active image configuration when the active image changes."""

    def __init__(self, config_repository: ConfigRepository) -> None:
        self._config_repository = config_repository
        self._active_image_updated_signal = signal("active_image_updated")
        self._active_image_updated_signal.connect(self._on_active_image_updated)

    async def _on_active_image_updated(self, active_image: Image) -> None:
        """Update the current active image configuration in the database."""
        self._config_repository.set(ConfigKey.CURRENT_ACTIVE_IMAGE, active_image.id)
        self._config_repository.set(
            ConfigKey.CURRENT_ACTIVE_IMAGE_SINCE, datetime.datetime.now(tz=datetime.UTC).isoformat()
        )
