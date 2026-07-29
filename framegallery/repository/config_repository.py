import json
import logging
from enum import Enum
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from framegallery.models import Config

logger = logging.getLogger("framegallery")


class ConfigKey(Enum):
    """Keys for the configuration in the database."""

    SLIDESHOW_ENABLED = "slideshow_enabled"
    SLIDESHOW_INTERVAL = "slideshow_interval"
    CURRENT_ACTIVE_IMAGE = "current_active_image"
    CURRENT_ACTIVE_IMAGE_SINCE = "current_active_image_since"
    ACTIVE_FILTER = "active_filter"
    AUTO_CLEANUP_ENABLED = "auto_cleanup_enabled"
    TV_WATCH_MODE_ENABLED = "tv_watch_mode_enabled"
    # Bookkeeping for images this app has put on the TV: the one currently displayed,
    # and any we still owe the TV a delete for. Persisted so a restart cannot lose
    # track of them (see UploadProcessor.record_uploaded).
    LATEST_TV_CONTENT_ID = "latest_tv_content_id"
    PENDING_TV_DELETIONS = "pending_tv_deletions"


class ConfigRepository:
    """Manages the configuration in the database."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, key: ConfigKey) -> Config | None:
        """Get a configuration value by its key."""
        stmt = select(Config).where(Config.key == key.value)

        return self._db.execute(stmt).scalar_one_or_none()

    def get_or(self, key: ConfigKey, default_value: Any | None = None) -> Config:  # noqa: ANN401
        """Get a configuration value by its key or return the default value."""
        value_from_db = self.get(key)
        if value_from_db is None:
            return Config(key=key.value, value=default_value)

        return value_from_db

    def get_bool(self, key: ConfigKey, *, default: bool = False) -> bool:
        """
        Get a configuration value interpreted as a boolean.

        Boolean values are stored as the JSON strings ``"true"``/``"false"`` (see
        ``set``), but an unset key falls back to the raw ``default`` bool. This
        helper normalises both cases so callers don't scatter ``value == "true"``.
        """
        value = self.get_or(key, default_value=default).value
        if isinstance(value, str):
            return value.strip().lower() == "true"
        return bool(value)

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


def read_bool_setting(key: ConfigKey, *, default: bool = False) -> bool:
    """
    Read a boolean setting on a short-lived session of its own, falling back to ``default``.

    For callers outside the request cycle -- background loops and the upload
    processors -- which have no session injected and must observe the *current*
    value on every check rather than one captured at startup, so that toggling a
    setting in the UI takes effect immediately.

    These callers sit on the slideshow hot path, so a database that is missing,
    locked or mid-migration must not propagate an exception and take the push down
    with it. Any failure degrades to ``default``, which for every current caller is
    the permissive value.
    """
    # Imported here rather than at module scope: framegallery.dependencies pulls in
    # the upload processors, which in turn read settings through this helper.
    from framegallery.database import SessionLocal  # noqa: PLC0415

    try:
        with SessionLocal() as db:
            return ConfigRepository(db).get_bool(key, default=default)
    except SQLAlchemyError:
        logger.warning("Could not read setting %s; falling back to %s", key.value, default, exc_info=True)
        return default


def read_str_setting(key: ConfigKey, *, default: str | None = None) -> str | None:
    """
    Read a string setting on a short-lived session of its own.

    Separate from ``read_json_setting`` because ``ConfigRepository.set`` stores strings
    verbatim and JSON-encodes everything else. Feeding a raw string such as
    ``MY-F0009`` through ``json.loads`` raises, which would silently fall back to the
    default -- so string-valued settings must be read back as-is.
    """
    from framegallery.database import SessionLocal  # noqa: PLC0415

    try:
        with SessionLocal() as db:
            config = ConfigRepository(db).get(key)
    except SQLAlchemyError:
        logger.warning("Could not read setting %s; falling back to %s", key.value, default, exc_info=True)
        return default

    if config is None or config.value is None:
        return default
    return str(config.value)


def read_json_setting(key: ConfigKey, *, default: Any = None) -> Any:  # noqa: ANN401 -- mirrors the stored JSON
    """
    Read a JSON-encoded setting on a short-lived session of its own.

    Falls back to ``default`` if the key is unset, the database is unusable, or the
    stored text is not valid JSON -- see ``read_bool_setting`` for why these callers
    must not raise.
    """
    from framegallery.database import SessionLocal  # noqa: PLC0415

    try:
        with SessionLocal() as db:
            config = ConfigRepository(db).get(key)
            raw = config.value if config else None
    except SQLAlchemyError:
        logger.warning("Could not read setting %s; falling back to %s", key.value, default, exc_info=True)
        return default

    if raw is None:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        logger.warning("Setting %s holds invalid JSON (%r); falling back to %s", key.value, raw, default)
        return default


def write_setting(key: ConfigKey, value: Any) -> bool:  # noqa: ANN401 -- mirrors ConfigRepository.set
    """
    Write a setting on a short-lived session of its own; return whether it stuck.

    Callers on the slideshow hot path must keep going when the write fails, but they
    need to *know* it failed -- for the TV content bookkeeping, a lost write means an
    image on the TV that nothing will remember to delete.
    """
    from framegallery.database import SessionLocal  # noqa: PLC0415

    try:
        with SessionLocal() as db:
            ConfigRepository(db).set(key, value)
    except SQLAlchemyError:
        logger.warning("Could not persist setting %s", key.value, exc_info=True)
        return False
    return True
