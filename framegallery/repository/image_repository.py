from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from framegallery.models import Image


class ImageRepository:
    """Manages the images in the database."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_random_image(self) -> Image | None:
        """Get a random image from the database."""
        stmt = select(Image).order_by(func.random()).limit(1)

        return self._db.execute(stmt).scalar_one_or_none()

    def get_image_matching_filter(self, where_expression: ColumnElement[bool] | None) -> Image | None:
        """Get a random image that matches the given filter provided via the where_expression."""
        if where_expression is None:
            stmt = select(Image).order_by(func.random()).limit(1)
        else:
            stmt = select(Image).where(where_expression).order_by(func.random()).limit(1)

        return self._db.execute(stmt).scalar_one_or_none()


class NoImagesError(ValueError):
    """Raised when there are no images in the database."""

    def __init__(self) -> None:
        super().__init__("No images in database")
