from __future__ import annotations

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from framegallery.models import Base, Filter
from framegallery.repository.filter_repository import FilterRepository


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
def repository(db_session: Session) -> FilterRepository:
    """Return a FilterRepository using the provided session."""
    return FilterRepository(db_session)


def test_create_filter(repository: FilterRepository) -> None:
    """Test creating a filter and retrieving it by id."""
    filter_ = repository.create_filter("test_filter", "test query")
    assert filter_.name == "test_filter"
    assert filter_.query == "test query"
    assert filter_.id is not None
    filter_from_db = repository.get_filter(filter_.id)
    assert filter_from_db is not None
    assert filter_from_db.name == "test_filter"
    assert filter_from_db.query == "test query"


def test_get_filter_by_name(repository: FilterRepository, db_session: Session) -> None:
    """Test getting a filter by name."""
    db_session.add(Filter(name="test_filter", query="test query"))
    db_session.commit()
    result = repository.get_filter_by_name("test_filter")
    assert result is not None
    assert result.name == "test_filter"
    assert result.query == "test query"


def test_get_filter_by_id(repository: FilterRepository, db_session: Session) -> None:
    """Test getting a filter by id."""
    filter_ = Filter(name="test_filter", query="test query")
    db_session.add(filter_)
    db_session.commit()
    result = repository.get_filter(filter_.id)
    assert result is not None
    assert result.name == "test_filter"
    assert result.query == "test query"


def test_get_filters_returns_ordered_list(repository: FilterRepository, db_session: Session) -> None:
    """Test that get_filters returns filters ordered by name."""
    filters = [
        Filter(name="b_filter", query="query b"),
        Filter(name="a_filter", query="query a"),
    ]
    db_session.add_all(filters)
    db_session.commit()
    result = repository.get_filters()
    assert result is not None
    assert len(result) == 2  # noqa: PLR2004
    assert result[0].name == "a_filter"  # Should return first filter alphabetically
