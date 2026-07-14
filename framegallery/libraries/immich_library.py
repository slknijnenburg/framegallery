"""
An Immich album (or set of albums) exposed as a :class:`~framegallery.libraries.base.Library`.

Selection is the de-duplicated union of the configured albums' assets. That union is cached with a
short TTL so repeated slideshow ticks don't hammer the Immich server, and a random asset is picked
client-side (Immich's ``/search/random`` has been unreliable across releases).
"""

import logging
import secrets
import time
from dataclasses import dataclass

from framegallery.aspect_ratio import get_aspect_ratio
from framegallery.libraries.base import AlbumRef, Library, PhotoBytes, PhotoRef
from framegallery.libraries.immich_client import ImmichClient

logger = logging.getLogger("framegallery")

_CONTENT_TYPE_TO_SUFFIX = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/tiff": ".tiff",
    "image/heic": ".heic",
}


@dataclass(frozen=True)
class _Asset:
    asset_id: str
    width: int | None
    height: int | None
    filename: str | None


def _suffix_for_content_type(content_type: str) -> str:
    """Map an Immich content-type to a file extension the TV upload accepts."""
    return _CONTENT_TYPE_TO_SUFFIX.get(content_type.split(";")[0].strip().lower(), ".jpg")


class ImmichLibrary(Library):
    """A library backed by one or more Immich albums."""

    def __init__(self, client: ImmichClient, album_ids: list[str], library_id: str, ttl: float = 300.0) -> None:
        self.library_id = library_id
        self._client = client
        self._album_ids = album_ids
        self._ttl = ttl
        self._assets: list[_Asset] = []
        self._assets_by_id: dict[str, _Asset] = {}
        self._cache_expiry: float = 0.0

    async def _ensure_assets(self) -> None:
        if self._cache_expiry > time.monotonic() and self._assets:
            return
        seen: dict[str, _Asset] = {}
        for album_id in self._album_ids:
            for raw in await self._client.get_album_assets(album_id):
                asset = self._parse_asset(raw)
                if asset is not None and asset.asset_id not in seen:
                    seen[asset.asset_id] = asset
        self._assets = list(seen.values())
        self._assets_by_id = seen
        self._cache_expiry = time.monotonic() + self._ttl
        logger.debug("Immich library %s cached %d assets", self.library_id, len(self._assets))

    @staticmethod
    def _parse_asset(raw: dict) -> _Asset | None:
        asset_id = raw.get("id")
        if not asset_id:
            return None
        exif = raw.get("exifInfo") or {}
        return _Asset(
            asset_id=asset_id,
            width=exif.get("exifImageWidth"),
            height=exif.get("exifImageHeight"),
            filename=raw.get("originalFileName"),
        )

    def _to_photo_ref(self, asset: _Asset) -> PhotoRef:
        aspect_width: int | None = None
        aspect_height: int | None = None
        if asset.width and asset.height:
            aspect_width, aspect_height = get_aspect_ratio(asset.width, asset.height)
        return PhotoRef(
            library_id=self.library_id,
            external_id=asset.asset_id,
            width=asset.width,
            height=asset.height,
            aspect_width=aspect_width,
            aspect_height=aspect_height,
            filename=asset.filename,
        )

    async def list_albums(self) -> list[AlbumRef]:
        """Return every album on the Immich server for selection in the UI."""
        albums = await self._client.get_albums()
        return [
            AlbumRef(
                id=album["id"],
                name=album.get("albumName", album["id"]),
                photo_count=album.get("assetCount"),
            )
            for album in albums
            if album.get("id")
        ]

    async def count_matching(self) -> int:
        """Return the number of (de-duplicated) assets across the configured albums."""
        await self._ensure_assets()
        return len(self._assets)

    async def pick_random(self) -> PhotoRef | None:
        """Return a random asset from the configured albums."""
        await self._ensure_assets()
        if not self._assets:
            return None
        return self._to_photo_ref(secrets.choice(self._assets))

    async def get_photo(self, external_id: str) -> PhotoRef | None:
        """Return metadata for a single asset, using the cached album data when available."""
        await self._ensure_assets()
        asset = self._assets_by_id.get(external_id)
        if asset is not None:
            return self._to_photo_ref(asset)
        # The asset isn't in the configured albums (e.g. it was moved); still allow byte fetches.
        return PhotoRef(library_id=self.library_id, external_id=external_id)

    async def fetch_bytes(self, photo: PhotoRef) -> PhotoBytes:
        """Download the original bytes for an asset from Immich."""
        data, content_type = await self._client.get_asset_original(photo.external_id)
        asset = self._assets_by_id.get(photo.external_id)
        width = asset.width if asset else photo.width
        height = asset.height if asset else photo.height
        return PhotoBytes(
            data=data,
            content_type=content_type,
            file_type_suffix=_suffix_for_content_type(content_type),
            width=width,
            height=height,
        )
