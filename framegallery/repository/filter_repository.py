
from sqlalchemy import Sequence, select
from sqlalchemy.orm import Session

from framegallery.models import Filter


class FilterRepository:
    """Manages the filters in the database."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_filters(self) -> Sequence[Filter] | None:
        """Get all filters from the database."""
        stmt = select(Filter).order_by(Filter.name)

        return self._db.execute(stmt).scalars().all()

    def get_filter_by_name(self, name: str) -> Filter | None:
        """Get a filter by its name."""
        stmt = select(Filter).where(Filter.name == name)

        return self._db.execute(stmt).scalar()

    def get_filter(self, filter_id: int) -> Filter | None:
        """Get a filter by its ID."""
        stmt = select(Filter).where(Filter.id == filter_id)

        return self._db.execute(stmt).scalar_one_or_none()

    def create_filter(self, name: str, query: str) -> Filter:
        """Create a new filter."""
        filter_ = Filter(name=name, query=query)

        self._db.add(filter_)
        self._db.commit()

        return filter_
