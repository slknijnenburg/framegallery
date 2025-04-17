import json
from enum import Enum
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from framegallery.models import Config


class ConfigKey(Enum):
    """Keys for the configuration in the database."""

    SLIDESHOW_ENABLED = "slideshow_enabled"
    SLIDESHOW_INTERVAL = "slideshow_interval"
    CURRENT_ACTIVE_IMAGE = "current_active_image"
    CURRENT_ACTIVE_IMAGE_SINCE = "current_active_image_since"
    ACTIVE_FILTER = "active_filter"

class ConfigRepository:
    """Manages the configuration in the database."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, key: ConfigKey) -> Config | None:
        """Get a configuration value by its key."""
        stmt = select(Config).where(Config.key == key.value)

        return self._db.execute(stmt).scalar_one_or_none()

    def get_or(self, key: ConfigKey, default_value: Any | None = None) -> Config: # noqa: ANN401
        """Get a configuration value by its key or return the default value."""
        value_from_db = self.get(key)
        if value_from_db is None:
            return Config(key=key.value, value=default_value)

        return value_from_db

    def set(self, key: ConfigKey, value: any) -> Config:
        """Set a configuration value by its key."""
        config = self.get_or(key)

        # if value is a string, store it directly, otherwise json encode it
        if isinstance(value, str):
            config.value = value
        else:
            config.value = json.dumps(value)

        self._db.add(config)
        self._db.commit()

        return config

    def delete(self, key: ConfigKey) -> None:
        """Delete a configuration value by its key."""
        stmt = delete(Config).where(Config.key == key.value)
        self._db.execute(stmt)
        self._db.commit()

    def has(self, key: ConfigKey) -> bool:
        """Check if a configuration value exists by its key."""
        return self.get(key) is not None
