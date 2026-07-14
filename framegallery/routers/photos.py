from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from framegallery.database import get_db
from framegallery.dependencies import get_library_manager
from framegallery.libraries.base import LibraryUnavailableError, PhotoRef
from framegallery.libraries.manager import LibraryManager
from framegallery.logging_config import setup_logging
from framegallery.repository.config_repository import ConfigKey, ConfigRepository
from framegallery.schemas import ActivePhoto

router = APIRouter(prefix="/api/photos", tags=["photos"])
logger = setup_logging()


def build_active_photo(photo: PhotoRef, source_type: str) -> ActivePhoto:
    """Build the API-facing ActivePhoto DTO from a PhotoRef and its source type."""
    return ActivePhoto(
        library_id=photo.library_id,
        external_id=photo.external_id,
        composite_id=photo.composite_id,
        source_type=source_type,
        is_local=source_type == "local",
        bytes_url=f"/api/photos/{photo.library_id}/{photo.external_id}/bytes",
        filename=photo.filename,
        width=photo.width,
        height=photo.height,
        aspect_width=photo.aspect_width,
        aspect_height=photo.aspect_height,
        keywords=photo.keywords,
    )


@router.get("/active", response_model=ActivePhoto | None)
async def get_active_photo(
    db: Annotated[Session, Depends(get_db)],
    manager: Annotated[LibraryManager, Depends(get_library_manager)],
) -> ActivePhoto | None:
    """Return metadata for the currently active photo, or null if none is set."""
    composite_id = ConfigRepository(db).get_or(ConfigKey.CURRENT_ACTIVE_IMAGE, default_value=None).value
    if not composite_id:
        return None
    described = await manager.describe(composite_id)
    if described is None:
        return None
    return build_active_photo(*described)


@router.get("/{library_id}/{external_id:path}/bytes")
async def get_photo_bytes(
    library_id: str,
    external_id: str,
    manager: Annotated[LibraryManager, Depends(get_library_manager)],
) -> Response:
    """Return the raw image bytes for a photo, dispatched through its owning library."""
    composite_id = f"{library_id}:{external_id}"
    try:
        photo_bytes = await manager.fetch_bytes(composite_id)
    except LibraryUnavailableError as exc:
        logger.warning("Could not fetch bytes for %s: %s", composite_id, exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Photo source unavailable") from exc

    return Response(content=photo_bytes.data, media_type=photo_bytes.content_type)
