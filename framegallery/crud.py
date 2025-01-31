from typing import Optional, Type

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .models import Image


def get_image_by_path(db: Session, filepath: str) -> Optional[Image]:
    stmt = select(Image).filter_by(filepath=filepath)

    return db.execute(stmt).scalar_one_or_none()


def get_image_by_id(db: Session, id: int) -> Optional[Image]:
    stmt = select(Image).filter_by(id=id)

    return db.execute(stmt).scalar_one_or_none()


# Get a random image from the database
def get_random_image(db: Session) -> Optional[Image]:
    stmt = select(Image).order_by(func.random()).limit(1)

    return db.execute(stmt).scalar_one_or_none()


def delete_images_not_in_processed_items_list(
    db: Session, processed_items: list
) -> list:
    """
    Delete all items that are not in the processed_items list via sqlalchemy 2.0
    :param db: Session
    :param processed_items: list[str]
    :return: list
    """
    stmt = delete(Image).where(~Image.filepath.in_(processed_items))
    result = db.execute(stmt)
    db.commit()

    return result.rowcount


def get_images(
    db: Session, skip: int = 0, limit: int | None = None
) -> list[Type[Image]]:
    return db.query(Image).order_by(Image.id.asc()).offset(skip).limit(limit).all()
