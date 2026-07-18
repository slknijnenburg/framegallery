from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from framegallery.database import get_db
from framegallery.frame_connector.processors import UploadProcessor
from framegallery.libraries.manager import LibraryManager
from framegallery.repository.config_repository import ConfigRepository
from framegallery.repository.filter_repository import FilterRepository
from framegallery.repository.image_repository import ImageRepository
from framegallery.repository.library_repository import LibraryRepository
from framegallery.slideshow.slideshow import Slideshow


def get_config_repository(db: Annotated[Session, Depends(get_db)]) -> ConfigRepository:
    """Get the configuration repository."""
    return ConfigRepository(db)


def get_image_repository(db: Annotated[Session, Depends(get_db)]) -> ImageRepository:
    """Get the image repository."""
    return ImageRepository(db)


def get_filter_repository(db: Annotated[Session, Depends(get_db)]) -> FilterRepository:
    """Get the filter repository."""
    return FilterRepository(db)


def get_library_repository(db: Annotated[Session, Depends(get_db)]) -> LibraryRepository:
    """Get the library repository."""
    return LibraryRepository(db)


def get_library_manager(request: Request) -> LibraryManager:
    """Get the shared LibraryManager instance from app state."""
    return request.app.state.library_manager


def get_slideshow_instance(
    library_manager: Annotated[LibraryManager, Depends(get_library_manager)],
) -> Slideshow:
    """Get the slideshow instance."""
    return Slideshow(library_manager)


def get_upload_processor(request: Request) -> UploadProcessor:
    """Get the active UploadProcessor instance from app state."""
    return request.app.state.upload_processor
