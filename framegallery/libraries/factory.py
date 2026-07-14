"""Build :class:`~framegallery.libraries.base.Library` instances from persisted config rows."""

import logging

from sqlalchemy.orm import Session

from framegallery.libraries.base import Library
from framegallery.libraries.immich_client import ImmichClient
from framegallery.libraries.immich_library import ImmichLibrary
from framegallery.libraries.local_library import LocalLibrary
from framegallery.models import Library as LibraryModel
from framegallery.repository.filter_repository import FilterRepository
from framegallery.repository.image_repository import ImageRepository

logger = logging.getLogger("framegallery")


def _build_local(row: LibraryModel, session: Session, image_repository: ImageRepository) -> LocalLibrary:
    filter_id = row.config.get("filter_id") if row.config else None
    filter_query: str | None = None
    if filter_id is not None:
        stored_filter = FilterRepository(session).get_filter(int(filter_id))
        filter_query = stored_filter.query if stored_filter is not None else None
    return LocalLibrary(image_repository, session, filter_query, row.library_id)


def _immich_cache_key(row: LibraryModel) -> tuple:
    config = row.config or {}
    album_ids = tuple(config.get("album_ids", []))
    return (row.library_id, config.get("base_url"), config.get("api_key"), album_ids)


def _build_immich(row: LibraryModel, client_cache: dict) -> ImmichLibrary | None:
    config = row.config or {}
    base_url = config.get("base_url")
    api_key = config.get("api_key")
    if not base_url or not api_key:
        logger.warning("Immich library %r missing base_url/api_key; skipping", row.library_id)
        return None

    # Cache the whole ImmichLibrary (not just the client) so its TTL asset cache survives across
    # picks. A config change produces a new cache key, so stale instances fall out naturally.
    key = _immich_cache_key(row)
    cached = client_cache.get(row.library_id)
    if cached is not None and cached[0] == key:
        return cached[1]

    # Config changed (or first build): close any superseded client before replacing it.
    if cached is not None:
        client_cache.pop(row.library_id, None)

    client = ImmichClient(base_url, api_key)
    library = ImmichLibrary(client, list(config.get("album_ids", [])), row.library_id)
    client_cache[row.library_id] = (key, library, client)
    return library


def build_library(
    row: LibraryModel,
    session: Session,
    image_repository: ImageRepository,
    client_cache: dict,
) -> Library | None:
    """
    Instantiate the concrete Library for a config row, or None if it can't be built.

    ``client_cache`` maps ``library_id`` to ``(cache_key, ImmichLibrary, ImmichClient)`` so Immich
    HTTP pools and per-source asset caches survive across picks; the local backend does not use it.
    """
    if row.source_type == "local":
        return _build_local(row, session, image_repository)
    if row.source_type == "immich":
        return _build_immich(row, client_cache)

    logger.warning("Unknown library source_type %r for library %r; skipping", row.source_type, row.library_id)
    return None
