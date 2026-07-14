from __future__ import annotations

from dataclasses import dataclass
from typing import Self

import pytest

from framegallery.libraries.base import (
    AlbumRef,
    Library,
    LibraryUnavailableError,
    PhotoBytes,
    PhotoRef,
)
from framegallery.libraries.manager import LibraryManager, _weighted_choice


@dataclass
class _Row:
    library_id: str
    weight: float = 1.0
    source_type: str = "fake"


class FakeLibrary(Library):
    """A minimal in-memory Library for exercising the manager without a DB or network."""

    def __init__(self, library_id: str, count: int, *, unavailable: bool = False) -> None:
        self.library_id = library_id
        self._count = count
        self._unavailable = unavailable

    async def list_albums(self) -> list[AlbumRef]:
        """Return no albums."""
        return []

    async def count_matching(self) -> int:
        """Return the configured count, or raise if marked unavailable."""
        if self._unavailable:
            error_message = "boom"
            raise LibraryUnavailableError(error_message)
        return self._count

    async def pick_random(self) -> PhotoRef | None:
        """Return a fixed PhotoRef."""
        return PhotoRef(library_id=self.library_id, external_id="1")

    async def get_photo(self, external_id: str) -> PhotoRef | None:
        """Return a PhotoRef for the given external id."""
        return PhotoRef(library_id=self.library_id, external_id=external_id)

    async def fetch_bytes(self, photo: PhotoRef) -> PhotoBytes:  # noqa: ARG002
        """Return dummy bytes."""
        return PhotoBytes(data=b"x", content_type="image/jpeg", file_type_suffix=".jpg")


def test_weighted_choice_distribution() -> None:
    """_weighted_choice picks proportionally to the supplied weights."""
    a = FakeLibrary("a", count=0)
    b = FakeLibrary("b", count=0)
    counts = {"a": 0, "b": 0}
    for _ in range(2000):
        chosen = _weighted_choice([a, b], [10.0, 90.0])
        counts[chosen.library_id] += 1

    # Expect roughly a 10:90 split; allow generous tolerance for randomness.
    ratio = counts["b"] / (counts["a"] + counts["b"])
    assert 0.80 < ratio < 0.97  # noqa: PLR2004


def test_weighted_choice_single_candidate() -> None:
    """A single candidate is always returned."""
    only = FakeLibrary("only", count=5)
    assert _weighted_choice([only], [5.0]) is only


@pytest.mark.asyncio
async def test_pick_photo_skips_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unreachable library is skipped and the pick comes from a healthy one."""
    manager = LibraryManager(session_factory=_null_session_factory)
    healthy = FakeLibrary("healthy", count=5)
    broken = FakeLibrary("broken", count=5, unavailable=True)
    monkeypatch.setattr(
        manager,
        "_enabled_libraries",
        lambda _session: [(_Row("broken"), broken), (_Row("healthy"), healthy)],
    )

    photo = await manager.pick_photo()
    assert photo is not None
    assert photo.library_id == "healthy"


@pytest.mark.asyncio
async def test_pick_photo_all_unavailable_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """When every library is unreachable, pick_photo returns None (loop keeps running)."""
    manager = LibraryManager(session_factory=_null_session_factory)
    broken = FakeLibrary("broken", count=5, unavailable=True)
    monkeypatch.setattr(manager, "_enabled_libraries", lambda _session: [(_Row("broken"), broken)])

    assert await manager.pick_photo() is None


@pytest.mark.asyncio
async def test_pick_photo_ignores_zero_count(monkeypatch: pytest.MonkeyPatch) -> None:
    """Libraries with no matching photos are not chosen."""
    manager = LibraryManager(session_factory=_null_session_factory)
    empty = FakeLibrary("empty", count=0)
    full = FakeLibrary("full", count=3)
    monkeypatch.setattr(
        manager,
        "_enabled_libraries",
        lambda _session: [(_Row("empty"), empty), (_Row("full"), full)],
    )

    photo = await manager.pick_photo()
    assert photo is not None
    assert photo.library_id == "full"


class _NullSession:
    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def _null_session_factory() -> _NullSession:
    return _NullSession()
