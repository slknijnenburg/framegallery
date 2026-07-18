from __future__ import annotations

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from framegallery.models import Base
from framegallery.repository.config_repository import ConfigKey, ConfigRepository


@pytest.fixture
def engine() -> Engine:
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def repository(engine: Engine) -> ConfigRepository:
    """Return a ConfigRepository using an in-memory session."""
    with Session(engine) as session:
        yield ConfigRepository(session)
        session.rollback()


def test_get_bool_missing_returns_default(repository: ConfigRepository) -> None:
    """An unset key falls back to the provided default bool."""
    assert repository.get_bool(ConfigKey.SLIDESHOW_ENABLED, default=True) is True
    assert repository.get_bool(ConfigKey.SLIDESHOW_ENABLED, default=False) is False


def test_get_bool_reads_stored_true(repository: ConfigRepository) -> None:
    """A bool set via set() (stored as the JSON string "true") reads back True."""
    repository.set(ConfigKey.SLIDESHOW_ENABLED, value=True)
    assert repository.get_bool(ConfigKey.SLIDESHOW_ENABLED, default=False) is True


def test_get_bool_reads_stored_false(repository: ConfigRepository) -> None:
    """A "false" string reads back False even when the default is True."""
    repository.set(ConfigKey.SLIDESHOW_ENABLED, "false")
    assert repository.get_bool(ConfigKey.SLIDESHOW_ENABLED, default=True) is False
