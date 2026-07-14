"""
The local filesystem gallery exposed as a :class:`~framegallery.libraries.base.Library`.

This wraps the existing local pipeline (``ImageRepository`` + ``QueryBuilder`` + ``read_file_data``)
so the blended slideshow can treat the local gallery like any other source. Selection is driven by
the library's configured react-querybuilder filter rather than by albums.
"""

import logging

from sqlalchemy.orm import Session

from framegallery import crud
from framegallery.image_manipulation import get_cropped_image_dimensions, read_file_data
from framegallery.libraries.base import AlbumRef, Library, LibraryUnavailableError, PhotoBytes, PhotoRef
from framegallery.models import Image
from framegallery.repository.filters.query_builder import QueryBuilder
from framegallery.repository.image_repository import ImageRepository

logger = logging.getLogger("framegallery")

_SUFFIX_TO_CONTENT_TYPE = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
}


def _content_type_for_suffix(suffix: str) -> str:
    """Map a file extension to a MIME type, defaulting to octet-stream."""
    return _SUFFIX_TO_CONTENT_TYPE.get(suffix.lower(), "application/octet-stream")


class LocalLibrary(Library):
    """A library backed by the local ``images`` table and filesystem."""

    def __init__(
        self,
        image_repository: ImageRepository,
        session: Session,
        filter_query: str | None,
        library_id: str = "local",
    ) -> None:
        self.library_id = library_id
        self._image_repository = image_repository
        self._session = session
        self._filter_query = filter_query

    def _where_expression(self):  # noqa: ANN202 - SQLAlchemy ColumnElement | None
        if not self._filter_query:
            return None
        return QueryBuilder(self._filter_query).build()

    async def list_albums(self) -> list[AlbumRef]:
        """Local selection uses query filters, not albums, so there are none to list."""
        return []

    async def count_matching(self) -> int:
        """Count local images matching the configured filter."""
        return self._image_repository.count_matching_filter(self._where_expression())

    async def pick_random(self) -> PhotoRef | None:
        """Return a random local image matching the configured filter."""
        image = self._image_repository.get_image_matching_filter(self._where_expression())
        if image is None:
            return None
        return self._to_photo_ref(image)

    async def get_photo(self, external_id: str) -> PhotoRef | None:
        """Return metadata for a single local image, or None if it no longer exists."""
        image = crud.get_image_by_id(self._session, int(external_id))
        return self._to_photo_ref(image) if image is not None else None

    async def fetch_bytes(self, photo: PhotoRef) -> PhotoBytes:
        """Read the image bytes from disk, applying any stored crop."""
        image = crud.get_image_by_id(self._session, int(photo.external_id))
        if image is None:
            error_message = f"Local image {photo.external_id} not found"
            raise LibraryUnavailableError(error_message)

        file_data, file_type_suffix = read_file_data(image)
        # read_file_data re-encodes cropped images as JPEG, so recompute the final dimensions.
        width, height = get_cropped_image_dimensions(image)
        return PhotoBytes(
            data=file_data,
            content_type=_content_type_for_suffix(file_type_suffix),
            file_type_suffix=file_type_suffix,
            width=width,
            height=height,
        )

    def _to_photo_ref(self, image: Image) -> PhotoRef:
        return PhotoRef(
            library_id=self.library_id,
            external_id=str(image.id),
            width=image.width,
            height=image.height,
            aspect_width=image.aspect_width,
            aspect_height=image.aspect_height,
            filename=image.filename,
            keywords=image.keywords,
        )
