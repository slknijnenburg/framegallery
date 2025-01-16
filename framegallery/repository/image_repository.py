from typing import Optional

from sqlalchemy import BinaryExpression, func, select
from sqlalchemy.orm import Session

from framegallery.models import Image


class ImageRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_random_image(self) -> Optional[Image]:
        stmt = select(Image).order_by(func.random()).limit(1)

        return self._db.execute(stmt).scalar_one_or_none()

    def get_image_matching_filter(self, where_expression: BinaryExpression|None) -> Optional[Image]:
        if where_expression is None:
            stmt = select(Image).order_by(func.random()).limit(1)
        else:
            stmt = select(Image).where(where_expression).order_by(func.random()).limit(1)

        return self._db.execute(stmt).scalar_one_or_none()