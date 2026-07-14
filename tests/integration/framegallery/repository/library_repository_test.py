from __future__ import annotations

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from framegallery.models import Base, Library
from framegallery.repository.library_repository import LibraryRepository


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


@pytest.fixture
def repository(db_session: Session) -> LibraryRepository:
    """Return a LibraryRepository using the provided session."""
    return LibraryRepository(db_session)


def test_save_and_get_by_library_id(repository: LibraryRepository) -> None:
    """A saved library is retrievable by its stable library_id."""
    library = Library(
        library_id="immich-1",
        name="My Immich",
        source_type="immich",
        enabled=True,
        weight=2.0,
        config={"base_url": "http://immich.local", "album_ids": ["a"]},
    )
    saved = repository.save(library)
    assert saved.id is not None

    fetched = repository.get_by_library_id("immich-1")
    assert fetched is not None
    assert fetched.name == "My Immich"
    assert fetched.weight == 2.0  # noqa: PLR2004
    assert fetched.config["base_url"] == "http://immich.local"


def test_get_all_enabled_only(repository: LibraryRepository, db_session: Session) -> None:
    """get_all(enabled_only=True) filters out disabled libraries."""
    db_session.add_all(
        [
            Library(library_id="local", name="Local", source_type="local", enabled=True, weight=1.0, config={}),
            Library(library_id="immich-1", name="Immich", source_type="immich", enabled=False, weight=1.0, config={}),
        ]
    )
    db_session.commit()

    assert len(repository.get_all()) == 2  # noqa: PLR2004
    enabled = repository.get_all(enabled_only=True)
    assert [lib.library_id for lib in enabled] == ["local"]


def test_delete(repository: LibraryRepository) -> None:
    """A deleted library is no longer retrievable."""
    library = repository.save(
        Library(library_id="immich-1", name="Immich", source_type="immich", enabled=True, weight=1.0, config={})
    )
    repository.delete(library.id)
    assert repository.get_by_library_id("immich-1") is None
