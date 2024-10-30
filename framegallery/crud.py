from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import ArtItem, Image
from .schemas import ArtItem as ArtItemSchema

def get_art_item(db: Session, content_id: str):
    return db.query(ArtItem).filter_by(content_id=content_id).first()

def get_art_items(db: Session, skip: int = 0, limit: int = 100):
    return db.query(ArtItem).order_by(ArtItem.content_id.asc()).offset(skip).limit(limit).all()

def create_art_item(db: Session, art_item: ArtItemSchema) -> ArtItem:
    db_art_item = ArtItem(**art_item.model_dump())
    db.add(db_art_item)
    db.commit()
    db.refresh(db_art_item)

    return db_art_item

def persist_art_item(db: Session, art_item: ArtItem) -> None:
    db.add(art_item)
    db.commit()


def get_artitem_by_path(db: Session, image_path: str) -> Optional[ArtItem]:
    stmt = select(ArtItem).filter_by(local_filename=image_path)

    return db.execute(stmt).scalar_one_or_none()


def delete_items_not_in_list(db: Session, processed_items: list) -> int:
    """
    Delete all items that are not in the processed_items list via sqlalchemy 2.0
    :param db: Session
    :param processed_items: list[str]
    :return: int The number of deleted items
    """
    stmt = delete(ArtItem).where(~ArtItem.content_id.in_(processed_items))
    result = db.execute(stmt)
    db.commit()

    return result.rowcount

def get_image_by_path(db: Session, filepath: str) -> Optional[Image]:
    stmt = select(Image).filter_by(filepath=filepath)

    return db.execute(stmt).scalar_one_or_none()

def delete_images_not_in_processed_items_list(db: Session, processed_items: list) -> list:
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
