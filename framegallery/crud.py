
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .models import Image


def get_image_by_path(db: Session, filepath: str) -> Image | None:
    """Retrieve an Image object by its filepath."""
    stmt = select(Image).filter_by(filepath=filepath)

    return db.execute(stmt).scalar_one_or_none()


def get_image_by_id(db: Session, image_id: int) -> Image | None:
    """Retrieve an Image object by its ID."""
    stmt = select(Image).filter_by(id=image_id)

    return db.execute(stmt).scalar_one_or_none()

def get_random_image(db: Session) -> Image | None:
    """Get a random image from the database."""
    stmt = select(Image).order_by(func.random()).limit(1)

    return db.execute(stmt).scalar_one_or_none()


def delete_images_not_in_processed_items_list(
    db: Session, processed_items: list[str]
) -> int:
    """Delete all items that are not in the processed_items list via sqlalchemy 2.0."""
    stmt = delete(Image).where(~Image.filepath.in_(processed_items))
    result = db.execute(stmt)
    db.commit()

    return result.rowcount


def get_images(
    db: Session, skip: int = 0, limit: int | None = None
) -> list[Image]:
    """Get all images from the database."""
    return db.query(Image).order_by(Image.id.asc()).offset(skip).limit(limit).all()
