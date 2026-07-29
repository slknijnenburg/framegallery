from __future__ import annotations

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

import framegallery.database as database_module
from framegallery.models import Base
from framegallery.repository.config_repository import (
    ConfigKey,
    ConfigRepository,
    read_bool_setting,
    read_json_setting,
    read_str_setting,
    write_setting,
)


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


def test_read_bool_setting_uses_its_own_session(engine: Engine, monkeypatch) -> None:  # noqa: ANN001
    """
    read_bool_setting opens its own session and observes committed values.

    The upload processors and background loops have no session injected, and must see
    a toggle flipped in the UI on the very next check rather than a value captured at
    startup.
    """
    monkeypatch.setattr(database_module, "SessionLocal", sessionmaker(bind=engine))

    assert read_bool_setting(ConfigKey.TV_WATCH_MODE_ENABLED, default=False) is False

    with Session(engine) as session:
        ConfigRepository(session).set(ConfigKey.TV_WATCH_MODE_ENABLED, value=True)

    assert read_bool_setting(ConfigKey.TV_WATCH_MODE_ENABLED, default=False) is True


def test_read_bool_setting_falls_back_when_the_database_is_unusable(monkeypatch) -> None:  # noqa: ANN001
    """
    An unreadable database degrades to the default instead of raising.

    This runs on the slideshow hot path via the upload processors, so a database that
    is missing, locked or mid-migration must not take the push down with it.
    """
    broken_engine = create_engine("sqlite:///:memory:")  # no tables created
    monkeypatch.setattr(database_module, "SessionLocal", sessionmaker(bind=broken_engine))

    assert read_bool_setting(ConfigKey.TV_WATCH_MODE_ENABLED, default=False) is False
    assert read_bool_setting(ConfigKey.SLIDESHOW_ENABLED, default=True) is True


def test_string_settings_round_trip(engine: Engine, monkeypatch) -> None:  # noqa: ANN001
    """
    A string written with write_setting reads back intact.

    ConfigRepository.set stores strings verbatim and JSON-encodes everything else, so
    reading a raw string such as "MY-F0009" back through json.loads would raise and
    silently yield the default -- losing exactly the TV bookkeeping it is meant to
    preserve across a restart.
    """
    monkeypatch.setattr(database_module, "SessionLocal", sessionmaker(bind=engine))

    assert write_setting(ConfigKey.LATEST_TV_CONTENT_ID, "MY-F0009") is True
    assert read_str_setting(ConfigKey.LATEST_TV_CONTENT_ID, default=None) == "MY-F0009"


def test_json_settings_round_trip(engine: Engine, monkeypatch) -> None:  # noqa: ANN001
    """A list written with write_setting reads back as the same list."""
    monkeypatch.setattr(database_module, "SessionLocal", sessionmaker(bind=engine))

    assert write_setting(ConfigKey.PENDING_TV_DELETIONS, ["A", "B"]) is True
    assert read_json_setting(ConfigKey.PENDING_TV_DELETIONS, default=[]) == ["A", "B"]


def test_unset_settings_return_their_default(engine: Engine, monkeypatch) -> None:  # noqa: ANN001
    """Nothing stored yet means the caller's default, not a crash."""
    monkeypatch.setattr(database_module, "SessionLocal", sessionmaker(bind=engine))

    assert read_str_setting(ConfigKey.LATEST_TV_CONTENT_ID, default=None) is None
    assert read_json_setting(ConfigKey.PENDING_TV_DELETIONS, default=[]) == []
