from sqlalchemy.orm import Session

from . import models, schemas

def get_art_item(db: Session, content_id: str):
    return db.query(models.ArtItem).filter(models.ArtItem.content_id == content_id).first()

def get_art_items(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.ArtItem).offset(skip).limit(limit).all()

def create_art_item(db: Session, art_item: schemas.ArtItem):
    db_art_item = models.ArtItem(**art_item.model_dump())
    db.add(db_art_item)
    db.commit()
    db.refresh(db_art_item)

    return db_art_item
