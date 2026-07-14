from __future__ import annotations

import json

import httpx
import pytest

from framegallery.libraries.base import PhotoRef
from framegallery.libraries.immich_client import ImmichClient
from framegallery.libraries.immich_library import ImmichLibrary

# Assets per album. Asset "2" is shared between album-a and album-b and must be de-duplicated.
_ALBUM_ASSETS = {
    "album-a": [
        {"id": "1", "originalFileName": "one.jpg", "exifInfo": {"exifImageWidth": 1920, "exifImageHeight": 1080}},
        {"id": "2", "originalFileName": "two.jpg", "exifInfo": {"exifImageWidth": 1000, "exifImageHeight": 1000}},
    ],
    "album-b": [
        {"id": "2", "originalFileName": "two.jpg", "exifInfo": {"exifImageWidth": 1000, "exifImageHeight": 1000}},
        {"id": "3", "originalFileName": "three.jpg", "exifInfo": {}},
    ],
}
_ALBUMS = [{"id": "album-a", "albumName": "A"}, {"id": "album-b", "albumName": "B"}]


def _library(handler, album_ids: list[str]) -> ImmichLibrary:  # noqa: ANN001
    client = ImmichClient("http://immich.local", "key", transport=httpx.MockTransport(handler))
    return ImmichLibrary(client, album_ids, "immich-1")


def _search_handler(counter: dict) -> object:
    """Mock the metadata-search endpoint, filtering to the single requested album (one page)."""

    def handler(request: httpx.Request) -> httpx.Response:
        counter["count"] = counter.get("count", 0) + 1
        if request.url.path == "/api/search/metadata":
            body = json.loads(request.content)
            album_id = body["albumIds"][0]
            items = _ALBUM_ASSETS.get(album_id, [])
            return httpx.Response(
                200, json={"assets": {"items": items, "total": len(items), "count": len(items), "nextPage": None}}
            )
        if request.url.path == "/api/albums":
            return httpx.Response(200, json=_ALBUMS)
        if request.url.path.startswith("/api/assets/") and request.url.path.endswith("/original"):
            return httpx.Response(200, content=b"\x89PNG", headers={"content-type": "image/png"})
        return httpx.Response(404)

    return handler


@pytest.mark.asyncio
async def test_count_dedupes_across_albums() -> None:
    """The asset union across albums is de-duplicated by id."""
    library = _library(_search_handler({}), ["album-a", "album-b"])
    assert await library.count_matching() == 3  # 1, 2, 3 (2 shared)  # noqa: PLR2004


@pytest.mark.asyncio
async def test_cache_avoids_refetch() -> None:
    """The album union is cached, so a second count does not refetch."""
    counter: dict = {}
    library = _library(_search_handler(counter), ["album-a"])
    await library.count_matching()
    first = counter["count"]
    await library.count_matching()
    assert counter["count"] == first  # no additional HTTP calls


@pytest.mark.asyncio
async def test_pick_random_sets_aspect_and_tolerates_missing_exif() -> None:
    """pick_random computes aspect from EXIF, and assets without EXIF still yield a PhotoRef."""
    library = _library(_search_handler({}), ["album-a", "album-b"])
    ids: set[str] = set()
    for _ in range(20):
        photo = await library.pick_random()
        assert photo is not None
        ids.add(photo.external_id)
    assert ids <= {"1", "2", "3"}

    photo = await library.get_photo("1")
    assert photo is not None
    assert (photo.aspect_width, photo.aspect_height) == (16, 9)

    no_exif = await library.get_photo("3")
    assert no_exif is not None
    assert no_exif.width is None


@pytest.mark.asyncio
async def test_fetch_bytes_maps_content_type_to_suffix() -> None:
    """fetch_bytes downloads the original and derives the file suffix from the content type."""
    library = _library(_search_handler({}), ["album-a"])
    photo_bytes = await library.fetch_bytes(PhotoRef(library_id="immich-1", external_id="1"))
    assert photo_bytes.content_type == "image/png"
    assert photo_bytes.file_type_suffix == ".png"
    assert photo_bytes.data == b"\x89PNG"


@pytest.mark.asyncio
async def test_list_albums() -> None:
    """list_albums maps the Immich album list to AlbumRefs."""
    library = _library(_search_handler({}), [])
    albums = await library.list_albums()
    assert {a.id for a in albums} == {"album-a", "album-b"}
    assert {a.name for a in albums} == {"A", "B"}


@pytest.mark.asyncio
async def test_paginates_until_next_page_is_null() -> None:
    """When Immich returns a nextPage, the client keeps fetching until it is null."""
    pages: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        page = body["page"]
        pages.append(page)
        if page == 1:
            return httpx.Response(
                200,
                json={
                    "assets": {
                        "items": [
                            {"id": "a", "exifInfo": {"exifImageWidth": 16, "exifImageHeight": 9}},
                        ],
                        "nextPage": 2,
                    }
                },
            )
        return httpx.Response(
            200,
            json={
                "assets": {
                    "items": [
                        {"id": "b", "exifInfo": {"exifImageWidth": 16, "exifImageHeight": 9}},
                    ],
                    "nextPage": None,
                }
            },
        )

    library = _library(handler, ["album-a"])
    assert await library.count_matching() == 2  # noqa: PLR2004
    assert pages == [1, 2]
