import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from framegallery.models import Base, Filter
from framegallery.repository.filter_repository import FilterRepository


@pytest.fixture
def engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(engine):
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture
def repository(db_session):
    return FilterRepository(db_session)


def test_create_filter(repository):
    filter_ = repository.create_filter("test_filter", "test query")

    assert filter_.name == "test_filter"
    assert filter_.query == "test query"
    assert filter_.id is not None

    filter_from_db = repository.get_filter(filter_.id)
    assert filter_from_db is not None
    assert filter_from_db.name == "test_filter"
    assert filter_from_db.query == "test query"


def test_get_filter_by_name(repository, db_session):
    db_session.add(Filter(name="test_filter", query="test query"))
    db_session.commit()

    result = repository.get_filter_by_name("test_filter")

    assert result is not None
    assert result.name == "test_filter"
    assert result.query == "test query"


def test_get_filter_by_id(repository, db_session):
    filter_ = Filter(name="test_filter", query="test query")
    db_session.add(filter_)
    db_session.commit()

    result = repository.get_filter(filter_.id)

    assert result is not None
    assert result.name == "test_filter"
    assert result.query == "test query"


def test_get_filters_returns_ordered_list(repository, db_session):
    filters = [
        Filter(name="b_filter", query="query b"),
        Filter(name="a_filter", query="query a"),
    ]
    db_session.add_all(filters)
    db_session.commit()

    result = repository.get_filters()

    assert result is not None
    assert len(result) == 2
    assert result[0].name == "a_filter"  # Should return first filter alphabetically
