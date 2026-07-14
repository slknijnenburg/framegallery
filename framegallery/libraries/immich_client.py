"""
Thin async HTTP client for the Immich REST API.

All Immich endpoint paths are centralized here so that Immich's (pre-1.0) API drift only needs
fixing in one place. Network/HTTP errors are translated into the library exception hierarchy from
:mod:`framegallery.libraries.base` so the manager can skip an unreachable source.
"""

import logging

import httpx

from framegallery.libraries.base import (
    ImmichAuthError,
    ImmichNotFoundError,
    ImmichUnavailableError,
)

logger = logging.getLogger("framegallery")

_HTTP_UNAUTHORIZED = 401
_HTTP_FORBIDDEN = 403
_HTTP_NOT_FOUND = 404
_HTTP_SERVER_ERROR = 500


def normalize_base_url(base_url: str) -> str:
    """Normalize an Immich base URL to the ``<scheme>://<host>[:port]/api`` form."""
    trimmed = base_url.strip().rstrip("/")
    if trimmed.endswith("/api"):
        return trimmed
    return f"{trimmed}/api"


class ImmichClient:
    """Async wrapper around the Immich REST API authenticated with an API key."""

    CONNECT_TIMEOUT = 5.0
    READ_TIMEOUT = 10.0
    DOWNLOAD_TIMEOUT = 30.0  # originals can be large, so allow a longer read for downloads
    SEARCH_PAGE_SIZE = 1000  # Immich caps metadata search at 1000 items per page

    def __init__(self, base_url: str, api_key: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._base = normalize_base_url(base_url)
        self._client = httpx.AsyncClient(
            headers={"x-api-key": api_key, "Accept": "application/json"},
            timeout=httpx.Timeout(self.READ_TIMEOUT, connect=self.CONNECT_TIMEOUT),
            transport=transport,
        )

    def _url(self, path: str) -> str:
        return f"{self._base}{path}"

    async def _get_json(self, path: str) -> dict | list:
        try:
            response = await self._client.get(self._url(path))
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            error_message = f"Immich request to {path} failed: {exc}"
            raise ImmichUnavailableError(error_message) from exc
        self._raise_for_status(response, path)
        return response.json()

    async def _post_json(self, path: str, body: dict) -> dict:
        try:
            response = await self._client.post(self._url(path), json=body)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            error_message = f"Immich request to {path} failed: {exc}"
            raise ImmichUnavailableError(error_message) from exc
        self._raise_for_status(response, path)
        result = response.json()
        if not isinstance(result, dict):
            error_message = f"Unexpected response payload for {path}"
            raise ImmichUnavailableError(error_message)
        return result

    @staticmethod
    def _raise_for_status(response: httpx.Response, path: str) -> None:
        if response.status_code in (_HTTP_UNAUTHORIZED, _HTTP_FORBIDDEN):
            error_message = f"Immich rejected the API key (HTTP {response.status_code})"
            raise ImmichAuthError(error_message)
        if response.status_code == _HTTP_NOT_FOUND:
            error_message = f"Immich resource not found: {path}"
            raise ImmichNotFoundError(error_message)
        if response.status_code >= _HTTP_SERVER_ERROR:
            error_message = f"Immich server error (HTTP {response.status_code}) for {path}"
            raise ImmichUnavailableError(error_message)

    async def get_albums(self) -> list[dict]:
        """Return all albums visible to the API key."""
        result = await self._get_json("/albums")
        return result if isinstance(result, list) else []

    async def get_album(self, album_id: str) -> dict:
        """Return a single album's metadata (without its assets)."""
        result = await self._get_json(f"/albums/{album_id}")
        if not isinstance(result, dict):
            error_message = f"Unexpected album payload for {album_id}"
            raise ImmichUnavailableError(error_message)
        return result

    async def get_album_assets(self, album_id: str) -> list[dict]:
        """
        Return every asset in an album via paginated metadata search.

        Recent Immich versions no longer embed assets in ``GET /albums/{id}``, so the assets are
        enumerated with ``POST /search/metadata`` filtered to this single album. ``albumIds`` uses
        AND semantics across ids, so callers must query one album at a time and de-duplicate.
        """
        assets: list[dict] = []
        page: int | None = 1
        while page is not None:
            body = {
                "albumIds": [album_id],
                "withExif": True,
                "size": self.SEARCH_PAGE_SIZE,
                "page": page,
            }
            bucket = (await self._post_json("/search/metadata", body)).get("assets", {})
            assets.extend(bucket.get("items", []))
            next_page = bucket.get("nextPage")
            page = int(next_page) if next_page else None
        return assets

    async def get_asset_original(self, asset_id: str) -> tuple[bytes, str]:
        """Download the original bytes of an asset, returning ``(data, content_type)``."""
        try:
            response = await self._client.get(
                self._url(f"/assets/{asset_id}/original"),
                timeout=httpx.Timeout(self.DOWNLOAD_TIMEOUT, connect=self.CONNECT_TIMEOUT),
            )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            error_message = f"Immich asset download failed: {exc}"
            raise ImmichUnavailableError(error_message) from exc
        self._raise_for_status(response, f"/assets/{asset_id}/original")
        content_type = response.headers.get("content-type", "application/octet-stream")
        return response.content, content_type

    async def ping(self) -> bool:
        """Return True if the Immich server responds to a ping."""
        try:
            await self._get_json("/server/ping")
        except ImmichNotFoundError:
            # Older Immich versions exposed the ping under /server-info/ping.
            await self._get_json("/server-info/ping")
        return True

    async def get_version(self) -> str | None:
        """Return the Immich server version string, or None if unavailable."""
        try:
            result = await self._get_json("/server/version")
        except ImmichUnavailableError:
            return None
        if isinstance(result, dict):
            parts = [str(result.get(k)) for k in ("major", "minor", "patch") if result.get(k) is not None]
            return ".".join(parts) if parts else None
        return None

    async def aclose(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._client.aclose()
