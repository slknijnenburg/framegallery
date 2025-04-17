from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from framegallery.models import Filter


class FilterRepository:
    """Manages the filters in the database."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_filters(self, skip: int = 0, limit: int = 100) -> list[Filter]:
        """Get all filters from the database."""
        stmt = select(Filter).order_by(Filter.name).offset(skip).limit(limit)
        result = self._db.execute(stmt).scalars().all()
        return list(result) if result is not None else []

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

    def delete_filter(self, filter_id: int) -> None:
        """Delete a filter by its ID."""
        stmt = delete(Filter).where(Filter.id == filter_id)
        self._db.execute(stmt)
        self._db.commit()

    def update_filter(self, filter_to_update: Filter, filter_id: int) -> Filter:
        """Update a filter by its ID."""
        stmt = (
            update(Filter).where(Filter.id == filter_id).values(
                name=filter_to_update.name,
                query=filter_to_update.query
            )
        )
        self._db.execute(stmt)
        self._db.commit()

        return filter_to_update
