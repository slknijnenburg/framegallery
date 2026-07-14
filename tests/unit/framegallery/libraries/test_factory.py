from __future__ import annotations

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from framegallery.libraries.factory import build_library
from framegallery.libraries.immich_library import ImmichLibrary
from framegallery.libraries.local_library import LocalLibrary
from framegallery.models import Base, Filter, Library
from framegallery.repository.image_repository import ImageRepository


@pytest.fixture
def engine() -> Engine:
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(engine: Engine) -> Session:
    """Yield a SQLAlchemy session bound to the test engine."""
    with Session(engine) as session:
        yield session
        session.rollback()


def test_build_local_library_with_filter(db_session: Session) -> None:
    """A local row resolves its configured filter's query into a LocalLibrary."""
    filter_row = Filter(name="wide", query='{"combinator":"and","rules":[]}')
    db_session.add(filter_row)
    db_session.commit()
    row = Library(
        library_id="local",
        name="Local",
        source_type="local",
        enabled=True,
        weight=1.0,
        config={"filter_id": filter_row.id},
    )

    library = build_library(row, db_session, ImageRepository(db_session), {})
    assert isinstance(library, LocalLibrary)


def test_build_immich_library_and_cache_reuse(db_session: Session) -> None:
    """Immich libraries are cached per config so the TTL asset cache survives across builds."""
    row = Library(
        library_id="immich-1",
        name="Immich",
        source_type="immich",
        enabled=True,
        weight=1.0,
        config={"base_url": "http://immich.local", "api_key": "k", "album_ids": ["a"]},
    )
    cache: dict = {}

    first = build_library(row, db_session, ImageRepository(db_session), cache)
    second = build_library(row, db_session, ImageRepository(db_session), cache)
    assert isinstance(first, ImmichLibrary)
    assert first is second  # same instance reused from the cache


def test_build_immich_new_instance_on_config_change(db_session: Session) -> None:
    """Changing the config produces a fresh ImmichLibrary (new cache key)."""
    cache: dict = {}
    row = Library(
        library_id="immich-1",
        name="Immich",
        source_type="immich",
        enabled=True,
        weight=1.0,
        config={"base_url": "http://immich.local", "api_key": "k", "album_ids": ["a"]},
    )
    first = build_library(row, db_session, ImageRepository(db_session), cache)

    row.config = {"base_url": "http://immich.local", "api_key": "k", "album_ids": ["a", "b"]}
    second = build_library(row, db_session, ImageRepository(db_session), cache)
    assert first is not second


def test_build_immich_missing_credentials_returns_none(db_session: Session) -> None:
    """An Immich row without base_url/api_key is skipped."""
    row = Library(
        library_id="immich-1",
        name="Immich",
        source_type="immich",
        enabled=True,
        weight=1.0,
        config={"album_ids": ["a"]},
    )
    assert build_library(row, db_session, ImageRepository(db_session), {}) is None


def test_build_unknown_source_returns_none(db_session: Session) -> None:
    """An unknown source_type is skipped."""
    row = Library(
        library_id="weird",
        name="Weird",
        source_type="dropbox",
        enabled=True,
        weight=1.0,
        config={},
    )
    assert build_library(row, db_session, ImageRepository(db_session), {}) is None
