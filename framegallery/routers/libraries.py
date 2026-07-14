from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from framegallery.dependencies import get_library_manager, get_library_repository
from framegallery.libraries.manager import LibraryManager
from framegallery.models import Library
from framegallery.repository.library_repository import LibraryRepository
from framegallery.schemas import (
    AlbumSummary,
    ConnectionTestResult,
    ImmichConnectionRequest,
    LibraryCreate,
    LibraryStatus,
    LibrarySummary,
    LibraryUpdate,
)

router = APIRouter(prefix="/api/libraries", tags=["libraries"])


def _to_summary(library: Library) -> LibrarySummary:
    """Build the API view of a library, deliberately omitting the stored API key."""
    config = library.config or {}
    return LibrarySummary(
        id=library.id,
        library_id=library.library_id,
        name=library.name,
        source_type=library.source_type,
        enabled=library.enabled,
        weight=library.weight,
        is_local=library.source_type == "local",
        has_api_key=bool(config.get("api_key")),
        base_url=config.get("base_url"),
        album_ids=config.get("album_ids", []),
        filter_id=config.get("filter_id"),
    )


@router.get("")
def list_libraries(
    library_repository: Annotated[LibraryRepository, Depends(get_library_repository)],
) -> list[LibrarySummary]:
    """List all configured libraries."""
    return [_to_summary(library) for library in library_repository.get_all()]


@router.get("/status")
async def library_status(
    manager: Annotated[LibraryManager, Depends(get_library_manager)],
) -> list[LibraryStatus]:
    """Return each library's live matching-photo count (or error), for surfacing in the UI."""
    return [LibraryStatus(**status_entry) for status_entry in await manager.library_status()]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_library(
    payload: LibraryCreate,
    library_repository: Annotated[LibraryRepository, Depends(get_library_repository)],
) -> LibrarySummary:
    """Create a new external library (currently Immich only)."""
    if payload.source_type != "immich":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only 'immich' libraries can be created")

    # library_id must be unique; derive a stable slug and disambiguate with the row count.
    existing = library_repository.get_all()
    library_id = f"immich-{len(existing) + 1}"
    while library_repository.get_by_library_id(library_id) is not None:
        library_id = f"{library_id}x"

    library = Library(
        library_id=library_id,
        name=payload.name,
        source_type="immich",
        enabled=payload.enabled,
        weight=payload.weight,
        config={
            "base_url": payload.base_url,
            "api_key": payload.api_key,
            "album_ids": payload.album_ids,
        },
    )
    return _to_summary(library_repository.save(library))


@router.put("/{library_pk}")
def update_library(
    library_pk: int,
    payload: LibraryUpdate,
    library_repository: Annotated[LibraryRepository, Depends(get_library_repository)],
) -> LibrarySummary:
    """Update a library. Omitted fields (including api_key) are left unchanged."""
    library = library_repository.get(library_pk)
    if library is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library not found")

    if payload.name is not None:
        library.name = payload.name
    if payload.enabled is not None:
        library.enabled = payload.enabled
    if payload.weight is not None:
        library.weight = payload.weight

    # Copy the JSON config so SQLAlchemy detects the change and persists it.
    config = dict(library.config or {})
    if payload.base_url is not None:
        config["base_url"] = payload.base_url
    if payload.api_key:
        config["api_key"] = payload.api_key
    if payload.album_ids is not None:
        config["album_ids"] = payload.album_ids
    if payload.filter_id is not None:
        config["filter_id"] = payload.filter_id
    library.config = config

    return _to_summary(library_repository.save(library))


@router.delete("/{library_pk}", status_code=status.HTTP_204_NO_CONTENT)
def delete_library(
    library_pk: int,
    library_repository: Annotated[LibraryRepository, Depends(get_library_repository)],
) -> None:
    """Delete a library. The default local library should not be deleted."""
    library = library_repository.get(library_pk)
    if library is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library not found")
    if library.source_type == "local":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The local library cannot be deleted")
    library_repository.delete(library_pk)


@router.post("/test-connection")
async def test_connection(
    payload: ImmichConnectionRequest,
    manager: Annotated[LibraryManager, Depends(get_library_manager)],
) -> ConnectionTestResult:
    """Probe an Immich server with the given credentials."""
    result = await manager.test_connection(payload.base_url, payload.api_key)
    return ConnectionTestResult(**result)


@router.post("/albums")
async def list_albums(
    payload: ImmichConnectionRequest,
    manager: Annotated[LibraryManager, Depends(get_library_manager)],
) -> list[AlbumSummary]:
    """List the albums available on an Immich server for the album picker."""
    albums = await manager.list_albums_for(payload.base_url, payload.api_key)
    return [AlbumSummary(id=a.id, name=a.name, photo_count=a.photo_count) for a in albums]


def _stored_immich_credentials(library_repository: LibraryRepository, library_pk: int) -> tuple[str, str]:
    """
    Return ``(base_url, api_key)`` for a saved Immich library, or raise an HTTP error.

    Lets the edit UI test the connection and reload albums using the stored key, so the secret
    never has to be re-entered just to change the album selection.
    """
    library = library_repository.get(library_pk)
    if library is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library not found")
    if library.source_type != "immich":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not an Immich library")
    config = library.config or {}
    base_url = config.get("base_url")
    api_key = config.get("api_key")
    if not base_url or not api_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Library has no stored credentials")
    return base_url, api_key


@router.post("/{library_pk}/test-connection")
async def test_connection_stored(
    library_pk: int,
    library_repository: Annotated[LibraryRepository, Depends(get_library_repository)],
    manager: Annotated[LibraryManager, Depends(get_library_manager)],
) -> ConnectionTestResult:
    """Probe a saved Immich library using its stored credentials."""
    base_url, api_key = _stored_immich_credentials(library_repository, library_pk)
    result = await manager.test_connection(base_url, api_key)
    return ConnectionTestResult(**result)


@router.get("/{library_pk}/albums")
async def list_albums_stored(
    library_pk: int,
    library_repository: Annotated[LibraryRepository, Depends(get_library_repository)],
    manager: Annotated[LibraryManager, Depends(get_library_manager)],
) -> list[AlbumSummary]:
    """List a saved Immich library's albums using its stored credentials."""
    base_url, api_key = _stored_immich_credentials(library_repository, library_pk)
    albums = await manager.list_albums_for(base_url, api_key)
    return [AlbumSummary(id=a.id, name=a.name, photo_count=a.photo_count) for a in albums]
