from __future__ import annotations

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from framegallery.models import Base, Image
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


@pytest.fixture
def repository(db_session: Session) -> ImageRepository:
    """Return an ImageRepository using the provided session."""
    return ImageRepository(db_session)


def _make_image(name: str, aspect_width: int) -> Image:
    return Image(
        filename=name,
        filepath=f"/images/{name}",
        filetype=".jpg",
        thumbnail_path=f"/images/{name}.thumbnail.jpg",
        width=1920,
        height=1080,
        aspect_width=aspect_width,
        aspect_height=9,
    )


def test_count_matching_filter_no_expression(repository: ImageRepository, db_session: Session) -> None:
    """With no filter, count_matching_filter counts every image."""
    db_session.add_all([_make_image("a.jpg", 16), _make_image("b.jpg", 16), _make_image("c.jpg", 4)])
    db_session.commit()

    assert repository.count_matching_filter(None) == 3  # noqa: PLR2004


def test_count_matching_filter_with_expression(repository: ImageRepository, db_session: Session) -> None:
    """count_matching_filter counts only images matching the where expression."""
    db_session.add_all([_make_image("a.jpg", 16), _make_image("b.jpg", 16), _make_image("c.jpg", 4)])
    db_session.commit()

    assert repository.count_matching_filter(Image.aspect_width == 16) == 2  # noqa: PLR2004


def test_count_matching_filter_empty(repository: ImageRepository) -> None:
    """count_matching_filter returns 0 when nothing matches."""
    assert repository.count_matching_filter(None) == 0
