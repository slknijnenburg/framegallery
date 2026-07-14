from __future__ import annotations

import pytest

from framegallery.libraries.base import (
    AlbumRef,
    ImmichAuthError,
    ImmichNotFoundError,
    ImmichUnavailableError,
    LibraryUnavailableError,
    PhotoBytes,
    PhotoRef,
    parse_composite_id,
)


def test_photo_ref_composite_id() -> None:
    """The composite id joins library id and external id with a colon."""
    ref = PhotoRef(library_id="immich-1", external_id="9f2c-abc", width=1920, height=1080)
    assert ref.composite_id == "immich-1:9f2c-abc"


def test_photo_ref_defaults() -> None:
    """Optional metadata defaults to None and a fresh extra dict."""
    ref = PhotoRef(library_id="local", external_id="123")
    assert ref.width is None
    assert ref.keywords is None
    assert ref.extra == {}
    # extra must not be a shared mutable default across instances.
    other = PhotoRef(library_id="local", external_id="456")
    assert ref.extra is not other.extra


def test_parse_composite_id_roundtrip() -> None:
    """parse_composite_id inverts composite_id, splitting on the first colon."""
    library_id, external_id = parse_composite_id("local:123")
    assert (library_id, external_id) == ("local", "123")


def test_parse_composite_id_external_id_with_colon() -> None:
    """Only the first colon is a separator, so external ids may contain colons."""
    library_id, external_id = parse_composite_id("immich-1:a:b:c")
    assert (library_id, external_id) == ("immich-1", "a:b:c")


def test_parse_composite_id_requires_colon() -> None:
    """A value without a colon is rejected."""
    with pytest.raises(ValueError, match="missing ':'"):
        parse_composite_id("2117")


def test_album_ref_and_photo_bytes() -> None:
    """Value objects carry the expected fields."""
    album = AlbumRef(id="abc", name="Holidays", photo_count=42)
    assert (album.id, album.name, album.photo_count) == ("abc", "Holidays", 42)

    photo_bytes = PhotoBytes(data=b"jpegdata", content_type="image/jpeg", file_type_suffix=".jpg", width=16, height=9)
    assert photo_bytes.data == b"jpegdata"
    assert photo_bytes.file_type_suffix == ".jpg"


def test_immich_errors_are_library_unavailable() -> None:
    """Immich-specific errors subclass LibraryUnavailableError so the manager can skip them."""
    for error_cls in (ImmichUnavailableError, ImmichAuthError, ImmichNotFoundError):
        assert issubclass(error_cls, LibraryUnavailableError)
