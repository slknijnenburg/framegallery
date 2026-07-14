"""
Source-agnostic value objects and the ``Library`` abstract base class.

These types decouple the slideshow pipeline from the local filesystem ``Image`` model so
that photos can originate from any backend (local gallery, Immich, ...). A photo is identified
across the system by its *composite id* ``"<library_id>:<external_id>"`` (e.g. ``local:123`` or
``immich-1:9f2c...``).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PhotoRef:
    """A normalized reference to a single photo from any library."""

    library_id: str
    external_id: str
    width: int | None = None
    height: int | None = None
    aspect_width: int | None = None
    aspect_height: int | None = None
    filename: str | None = None
    keywords: list[str] | None = None
    # Opaque per-source payload (e.g. Immich EXIF blob) that the owning library may use.
    extra: dict = field(default_factory=dict)

    @property
    def composite_id(self) -> str:
        """Return the stable ``"<library_id>:<external_id>"`` identifier."""
        return f"{self.library_id}:{self.external_id}"


@dataclass(frozen=True)
class AlbumRef:
    """A selectable container of photos within a library."""

    id: str
    name: str
    photo_count: int | None = None


@dataclass(frozen=True)
class PhotoBytes:
    """The raw bytes of a photo, ready to upload to the TV or serve to the browser."""

    data: bytes
    content_type: str
    file_type_suffix: str
    # Final (post-crop) pixel dimensions, used to pick the TV matte. May be None if unknown.
    width: int | None = None
    height: int | None = None


class Library(ABC):
    """
    A pluggable source of photos.

    Implementations map their backend onto :class:`PhotoRef` / :class:`PhotoBytes` so the
    slideshow and TV uploader can stay source-agnostic.
    """

    library_id: str

    @abstractmethod
    async def list_albums(self) -> list[AlbumRef]:
        """
        Return the albums/containers available for configuring selection.

        Album-less sources (e.g. the local gallery, which uses query filters instead) return
        an empty list.
        """

    @abstractmethod
    async def count_matching(self) -> int:
        """Return the number of photos matching this library's configured selection."""

    @abstractmethod
    async def pick_random(self) -> PhotoRef | None:
        """Return a random photo matching this library's selection, or None if empty."""

    @abstractmethod
    async def get_photo(self, external_id: str) -> PhotoRef | None:
        """Return metadata for a single photo by its external id, or None if not found."""

    @abstractmethod
    async def fetch_bytes(self, photo: PhotoRef) -> PhotoBytes:
        """Return the image bytes for the given photo."""

    async def health_check(self) -> bool:
        """
        Return True if the library is reachable and configured correctly.

        The default implementation treats a successful ``count_matching`` as healthy.
        """
        try:
            await self.count_matching()
        except LibraryUnavailableError:
            return False
        return True


def parse_composite_id(composite_id: str) -> tuple[str, str]:
    """
    Split a ``"<library_id>:<external_id>"`` string into its two parts.

    Splits on the first colon so external ids may themselves contain colons.
    """
    library_id, separator, external_id = composite_id.partition(":")
    if not separator:
        error_message = f"Invalid composite id (missing ':'): {composite_id!r}"
        raise ValueError(error_message)
    return library_id, external_id


class LibraryUnavailableError(Exception):
    """
    Raised when a library cannot be reached or is misconfigured.

    The :class:`~framegallery.libraries.manager.LibraryManager` catches this during blending and
    skips the offending library so the slideshow keeps running.
    """


class ImmichUnavailableError(LibraryUnavailableError):
    """Raised when the Immich server is unreachable, times out, or returns a server error."""


class ImmichAuthError(LibraryUnavailableError):
    """Raised when Immich rejects the API key (HTTP 401/403)."""


class ImmichNotFoundError(LibraryUnavailableError):
    """Raised when an Immich resource (album/asset) does not exist (HTTP 404)."""
