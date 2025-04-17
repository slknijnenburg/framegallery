from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from framegallery.database import get_db
from framegallery.repository.config_repository import ConfigRepository
from framegallery.repository.filter_repository import FilterRepository
from framegallery.repository.image_repository import ImageRepository
from framegallery.slideshow.slideshow import Slideshow


def get_config_repository(db: Annotated[Session,  Depends(get_db)]) -> ConfigRepository:
    """Get the configuration repository."""
    return ConfigRepository(db)

def get_image_repository(db: Annotated[Session,  Depends(get_db)]) -> ImageRepository:
    """Get the image repository."""
    return ImageRepository(db)

def get_filter_repository(db: Annotated[Session,  Depends(get_db)]) -> FilterRepository:
    """Get the filter repository."""
    return FilterRepository(db)

def get_slideshow_instance(
    image_repository: Annotated[ImageRepository, Depends(get_image_repository)],
    config_repository: Annotated[ConfigRepository, Depends(get_config_repository)],
    filter_repository: Annotated[FilterRepository, Depends(get_filter_repository)],
) -> Slideshow:
    """Get the slideshow instance."""
    return Slideshow(image_repository, config_repository, filter_repository)
