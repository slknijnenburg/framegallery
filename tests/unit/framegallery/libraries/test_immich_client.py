from __future__ import annotations

import httpx
import pytest

from framegallery.libraries.base import ImmichAuthError, ImmichNotFoundError, ImmichUnavailableError
from framegallery.libraries.immich_client import ImmichClient, normalize_base_url


def test_normalize_base_url() -> None:
    """The base URL is normalized to end with a single /api segment."""
    assert normalize_base_url("http://immich.local") == "http://immich.local/api"
    assert normalize_base_url("http://immich.local/") == "http://immich.local/api"
    assert normalize_base_url("http://immich.local/api") == "http://immich.local/api"
    assert normalize_base_url("http://immich.local/api/") == "http://immich.local/api"


def _client(handler) -> ImmichClient:  # noqa: ANN001
    return ImmichClient("http://immich.local", "secret-key", transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_sends_api_key_and_hits_expected_path() -> None:
    """Requests carry the x-api-key header and target /api/albums."""
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["api_key"] = request.headers.get("x-api-key")
        return httpx.Response(200, json=[{"id": "a1", "albumName": "Trip", "assetCount": 3}])

    client = _client(handler)
    albums = await client.get_albums()
    await client.aclose()

    assert captured["api_key"] == "secret-key"
    assert captured["url"] == "http://immich.local/api/albums"
    assert albums[0]["albumName"] == "Trip"


@pytest.mark.asyncio
async def test_auth_error_mapped() -> None:
    """A 401 becomes ImmichAuthError."""
    client = _client(lambda _request: httpx.Response(401))
    with pytest.raises(ImmichAuthError):
        await client.get_albums()
    await client.aclose()


@pytest.mark.asyncio
async def test_not_found_mapped() -> None:
    """A 404 becomes ImmichNotFoundError."""
    client = _client(lambda _request: httpx.Response(404))
    with pytest.raises(ImmichNotFoundError):
        await client.get_album("missing")
    await client.aclose()


@pytest.mark.asyncio
async def test_server_error_mapped() -> None:
    """A 500 becomes ImmichUnavailableError."""
    client = _client(lambda _request: httpx.Response(500))
    with pytest.raises(ImmichUnavailableError):
        await client.get_albums()
    await client.aclose()


@pytest.mark.asyncio
async def test_transport_error_mapped() -> None:
    """A transport-level failure becomes ImmichUnavailableError."""

    def handler(_request: httpx.Request) -> httpx.Response:
        error_message = "connection refused"
        raise httpx.ConnectError(error_message)

    client = _client(handler)
    with pytest.raises(ImmichUnavailableError):
        await client.get_albums()
    await client.aclose()


@pytest.mark.asyncio
async def test_get_asset_original_returns_bytes_and_type() -> None:
    """Downloading an asset returns its bytes and content type."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/assets/asset-1/original"
        return httpx.Response(200, content=b"\xff\xd8jpeg", headers={"content-type": "image/jpeg"})

    client = _client(handler)
    data, content_type = await client.get_asset_original("asset-1")
    await client.aclose()

    assert data == b"\xff\xd8jpeg"
    assert content_type == "image/jpeg"


@pytest.mark.asyncio
async def test_ping_falls_back_to_legacy_path() -> None:
    """When /server/ping 404s, the client retries the legacy /server-info/ping path."""
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path == "/api/server/ping":
            return httpx.Response(404)
        return httpx.Response(200, json={"res": "pong"})

    client = _client(handler)
    assert await client.ping() is True
    await client.aclose()
    assert "/api/server/ping" in paths
    assert "/api/server-info/ping" in paths
