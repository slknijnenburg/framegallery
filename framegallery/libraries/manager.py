"""
Blends photos across all enabled libraries and dispatches byte/metadata lookups.

The manager owns long-lived state (HTTP clients, caches) on ``app.state`` and opens short-lived
DB sessions per operation, so it can be shared by the slideshow background task, the TV uploader,
and request handlers without sharing a SQLAlchemy session across async contexts.
"""

import logging
import secrets
from collections.abc import Callable

from sqlalchemy.orm import Session

from framegallery.libraries.base import (
    AlbumRef,
    ImmichAuthError,
    Library,
    LibraryUnavailableError,
    PhotoBytes,
    PhotoRef,
    parse_composite_id,
)
from framegallery.libraries.factory import build_library
from framegallery.libraries.immich_client import ImmichClient
from framegallery.libraries.immich_library import ImmichLibrary
from framegallery.models import Library as LibraryModel
from framegallery.repository.image_repository import ImageRepository
from framegallery.repository.library_repository import LibraryRepository

logger = logging.getLogger("framegallery")


class LibraryManager:
    """Selects photos across enabled libraries with count-proportional weighting."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory
        # Long-lived per-source clients (e.g. Immich HTTP clients), reused across picks.
        self._client_cache: dict = {}

    def _enabled_libraries(self, session: Session) -> list[tuple[LibraryModel, Library]]:
        """Build the concrete Library objects for every enabled config row."""
        rows = LibraryRepository(session).get_all(enabled_only=True)
        image_repository = ImageRepository(session)
        libraries: list[tuple[LibraryModel, Library]] = []
        for row in rows:
            library = build_library(row, session, image_repository, self._client_cache)
            if library is not None:
                libraries.append((row, library))
        return libraries

    def _build_by_library_id(self, session: Session, library_id: str) -> Library | None:
        """Build a single library by its id regardless of enabled state (for byte/metadata lookups)."""
        row = LibraryRepository(session).get_by_library_id(library_id)
        if row is None:
            return None
        return build_library(row, session, ImageRepository(session), self._client_cache)

    async def pick_photo(self) -> PhotoRef | None:
        """
        Pick a random photo across enabled libraries, weighted by ``weight * matching_count``.

        Libraries that are unreachable are skipped so one bad source never stops the slideshow.
        """
        with self._session_factory() as session:
            libraries = self._enabled_libraries(session)

            candidates: list[Library] = []
            weights: list[float] = []
            for row, library in libraries:
                try:
                    count = await library.count_matching()
                except LibraryUnavailableError as exc:
                    logger.warning("Skipping library %r during pick: %s", row.library_id, exc)
                    continue
                if count > 0:
                    candidates.append(library)
                    weights.append(row.weight * count)

            if not candidates:
                logger.warning("No libraries have any matching photos")
                return None

            chosen = _weighted_choice(candidates, weights)
            try:
                return await chosen.pick_random()
            except LibraryUnavailableError as exc:
                logger.warning("Chosen library %r failed to return a photo: %s", chosen.library_id, exc)
                return None

    async def fetch_bytes(self, composite_id: str) -> PhotoBytes:
        """Return the image bytes for a photo identified by its composite id."""
        library_id, external_id = parse_composite_id(composite_id)
        with self._session_factory() as session:
            library = self._build_by_library_id(session, library_id)
            if library is None:
                error_message = f"Unknown library {library_id!r}"
                raise LibraryUnavailableError(error_message)
            photo = PhotoRef(library_id=library_id, external_id=external_id)
            return await library.fetch_bytes(photo)

    async def get_photo_metadata(self, composite_id: str) -> PhotoRef | None:
        """Return metadata for a photo identified by its composite id, or None if unavailable."""
        described = await self.describe(composite_id)
        return described[0] if described is not None else None

    async def describe(self, composite_id: str) -> tuple[PhotoRef, str] | None:
        """
        Return ``(PhotoRef, source_type)`` for a photo, or None if unavailable.

        ``source_type`` (e.g. "local"/"immich") comes from the owning library's config row, so
        callers can render source-aware UI without a second lookup.
        """
        library_id, external_id = parse_composite_id(composite_id)
        with self._session_factory() as session:
            row = LibraryRepository(session).get_by_library_id(library_id)
            if row is None:
                return None
            library = build_library(row, session, ImageRepository(session), self._client_cache)
            if library is None:
                return None
            try:
                photo = await library.get_photo(external_id)
            except LibraryUnavailableError as exc:
                logger.warning("Could not load metadata for %r: %s", composite_id, exc)
                return None
            if photo is None:
                return None
            return photo, row.source_type

    async def library_status(self) -> list[dict]:
        """
        Report each library's live matching-photo count (or error) for the UI.

        This makes the "no suitable images" condition visible in the frontend instead of only in
        the server logs.
        """
        with self._session_factory() as session:
            rows = LibraryRepository(session).get_all()
            image_repository = ImageRepository(session)
            statuses: list[dict] = []
            for row in rows:
                entry: dict = {
                    "id": row.id,
                    "library_id": row.library_id,
                    "enabled": row.enabled,
                    "count": None,
                    "error": None,
                }
                library = build_library(row, session, image_repository, self._client_cache)
                if library is None:
                    entry["error"] = "Library could not be initialised"
                else:
                    try:
                        entry["count"] = await library.count_matching()
                    except LibraryUnavailableError as exc:
                        entry["error"] = str(exc)
                statuses.append(entry)
            return statuses

    async def test_connection(self, base_url: str, api_key: str) -> dict:
        """Probe an Immich server, returning ``{ok, version?, error?}`` for the Libraries UI."""
        client = ImmichClient(base_url, api_key)
        try:
            await client.ping()
            version = await client.get_version()
        except ImmichAuthError:
            return {"ok": False, "error": "Invalid API key"}
        except LibraryUnavailableError as exc:
            return {"ok": False, "error": str(exc)}
        finally:
            await client.aclose()
        return {"ok": True, "version": version}

    async def list_albums_for(self, base_url: str, api_key: str) -> list[AlbumRef]:
        """List the albums available on an Immich server (for the album picker)."""
        client = ImmichClient(base_url, api_key)
        try:
            library = ImmichLibrary(client, [], "immich-probe")
            return await library.list_albums()
        finally:
            await client.aclose()

    async def aclose(self) -> None:
        """Close any long-lived clients held by the manager."""
        for entry in list(self._client_cache.values()):
            # Each entry is (cache_key, library, client); close the underlying HTTP client.
            client = entry[2] if isinstance(entry, tuple) and len(entry) >= 3 else None  # noqa: PLR2004
            aclose = getattr(client, "aclose", None)
            if aclose is not None:
                await aclose()
        self._client_cache.clear()


def _weighted_choice(candidates: list[Library], weights: list[float]) -> Library:
    """
    Pick one library with probability proportional to its weight.

    Uses ``secrets`` for the random draw to satisfy the linter's ban on the ``random`` module;
    cryptographic strength is irrelevant here but harmless.
    """
    total = sum(weights)
    threshold = secrets.randbelow(10_000_000) / 10_000_000 * total
    cumulative = 0.0
    for library, weight in zip(candidates, weights, strict=True):
        cumulative += weight
        if threshold < cumulative:
            return library
    return candidates[-1]
