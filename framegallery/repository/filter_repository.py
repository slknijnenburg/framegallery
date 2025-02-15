from typing import Optional

from sqlalchemy import select, Sequence
from sqlalchemy.orm import Session

from framegallery.models import Filter


class FilterRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_filters(self) -> Optional[Sequence[Filter]]:
        stmt = select(Filter).order_by(Filter.name)

        return self._db.execute(stmt).scalars().all()

    def get_filter_by_name(self, name: str) -> Optional[Filter]:
        stmt = select(Filter).where(Filter.name == name)

        return self._db.execute(stmt).scalar()

    def get_filter(self, filter_id: int) -> Optional[Filter]:
        stmt = select(Filter).where(Filter.id == filter_id)

        return self._db.execute(stmt).scalar_one_or_none()

    def create_filter(self, name: str, query: str) -> Filter:
        filter_ = Filter(name=name, query=query)

        self._db.add(filter_)
        self._db.commit()

        return filter_