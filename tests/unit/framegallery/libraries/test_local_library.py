from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PIL import Image as PILImage
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from framegallery.libraries.base import LibraryUnavailableError, PhotoRef
from framegallery.libraries.local_library import LocalLibrary
from framegallery.models import Base, Image
from framegallery.repository.image_repository import ImageRepository

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def engine() -> Engine:
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(engine: Engine) -> Session:
    """Yield a SQLAlchemy session bound to the test engine."""
    with Session(engine) as session:
        yield session
        session.rollback()


def _write_jpeg(path: Path, size: tuple[int, int] = (1920, 1080)) -> None:
    img = PILImage.new("RGB", size, color=(120, 30, 200))
    img.save(path, format="JPEG")


def _add_image(session: Session, path: str, *, aspect_width: int = 16) -> Image:
    image = Image(
        filename=path.rsplit("/", 1)[-1],
        filepath=path,
        filetype=".jpg",
        thumbnail_path=f"{path}.thumbnail.jpg",
        width=1920,
        height=1080,
        aspect_width=aspect_width,
        aspect_height=9,
        keywords=["holiday"],
    )
    session.add(image)
    session.commit()
    session.refresh(image)
    return image


@pytest.mark.asyncio
async def test_pick_random_maps_to_photo_ref(db_session: Session) -> None:
    """pick_random returns a PhotoRef carrying local metadata and a composite id."""
    image = _add_image(db_session, "/images/a.jpg")
    library = LocalLibrary(ImageRepository(db_session), db_session, filter_query=None)

    photo = await library.pick_random()

    assert photo is not None
    assert photo.library_id == "local"
    assert photo.external_id == str(image.id)
    assert photo.composite_id == f"local:{image.id}"
    assert photo.aspect_width == 16  # noqa: PLR2004
    assert photo.keywords == ["holiday"]


@pytest.mark.asyncio
async def test_count_matching_honours_filter(db_session: Session) -> None:
    """count_matching applies the library's react-querybuilder filter."""
    _add_image(db_session, "/images/wide.jpg", aspect_width=16)
    _add_image(db_session, "/images/other.jpg", aspect_width=4)

    query = '{"combinator": "and", "rules": [{"field": "aspect_ratio_width", "operator": "=", "value": 16}]}'
    library = LocalLibrary(ImageRepository(db_session), db_session, filter_query=query)

    assert await library.count_matching() == 1


@pytest.mark.asyncio
async def test_pick_random_empty_returns_none(db_session: Session) -> None:
    """pick_random returns None when no images match."""
    library = LocalLibrary(ImageRepository(db_session), db_session, filter_query=None)
    assert await library.pick_random() is None


@pytest.mark.asyncio
async def test_fetch_bytes_reads_file(db_session: Session, tmp_path: Path) -> None:
    """fetch_bytes reads the image from disk and reports its dimensions and mime type."""
    image_path = tmp_path / "photo.jpg"
    _write_jpeg(image_path)
    image = _add_image(db_session, str(image_path))

    library = LocalLibrary(ImageRepository(db_session), db_session, filter_query=None)
    photo = await library.pick_random()
    assert photo is not None

    photo_bytes = await library.fetch_bytes(photo)
    assert photo_bytes.content_type == "image/jpeg"
    assert photo_bytes.file_type_suffix == ".jpg"
    assert photo_bytes.data[:2] == b"\xff\xd8"  # JPEG magic bytes
    assert photo_bytes.width == 1920  # noqa: PLR2004
    assert photo_bytes.height == 1080  # noqa: PLR2004
    assert image.id is not None


@pytest.mark.asyncio
async def test_fetch_bytes_missing_row_raises(db_session: Session) -> None:
    """fetch_bytes raises LibraryUnavailableError when the image row is gone."""
    library = LocalLibrary(ImageRepository(db_session), db_session, filter_query=None)
    with pytest.raises(LibraryUnavailableError):
        await library.fetch_bytes(PhotoRef(library_id="local", external_id="999"))


@pytest.mark.asyncio
async def test_get_photo_and_list_albums(db_session: Session) -> None:
    """get_photo returns metadata by id; list_albums is empty for the local source."""
    image = _add_image(db_session, "/images/a.jpg")
    library = LocalLibrary(ImageRepository(db_session), db_session, filter_query=None)

    photo = await library.get_photo(str(image.id))
    assert photo is not None
    assert photo.external_id == str(image.id)

    assert await library.get_photo("12345") is None
    assert await library.list_albums() == []
