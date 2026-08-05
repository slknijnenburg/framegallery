"""Unit tests for upload payload normalization and the diagnostic payload copies."""

import io
from pathlib import Path

from PIL import Image as PILImage

from framegallery.image_manipulation import normalize_for_upload, store_upload_payload
from framegallery.libraries.base import PhotoBytes

MAX_WIDTH = 1920
MAX_HEIGHT = 1080
QUALITY = 90


def _encode(img: PILImage.Image, image_format: str = "JPEG", **kwargs: object) -> bytes:
    buffer = io.BytesIO()
    img.save(buffer, format=image_format, **kwargs)
    return buffer.getvalue()


def _photo(data: bytes, suffix: str = ".jpg", content_type: str = "image/jpeg") -> PhotoBytes:
    return PhotoBytes(data=data, content_type=content_type, file_type_suffix=suffix)


def _normalize(photo: PhotoBytes) -> PhotoBytes:
    return normalize_for_upload(photo, max_width=MAX_WIDTH, max_height=MAX_HEIGHT, jpeg_quality=QUALITY)


def test_oversized_jpeg_is_downscaled_to_fit() -> None:
    """An image larger than the box comes out resized to fit, still a JPEG."""
    photo = _photo(_encode(PILImage.new("RGB", (4000, 3000), "red")))

    result = _normalize(photo)

    decoded = PILImage.open(io.BytesIO(result.data))
    assert decoded.format == "JPEG"
    assert (result.width, result.height) == (1440, 1080)  # 4:3 fitted to the 1080p box
    assert (decoded.width, decoded.height) == (1440, 1080)
    assert result.file_type_suffix == ".jpg"
    assert result.content_type == "image/jpeg"


def test_fitting_jpeg_passes_through_byte_identical() -> None:
    """
    A JPEG already within the box is not re-encoded.

    This is deliberate do-no-harm: the pre-normalization pipeline sent such images
    verbatim and they worked, so re-encoding them would only cost quality.
    """
    data = _encode(PILImage.new("RGB", (1600, 900), "blue"))
    result = _normalize(_photo(data))

    assert result.data == data
    assert (result.width, result.height) == (1600, 900)


def test_never_upscales() -> None:
    """A tiny image stays tiny; fitting the box must not blow it up."""
    result = _normalize(_photo(_encode(PILImage.new("RGB", (300, 200), "green"))))

    assert (result.width, result.height) == (300, 200)


def test_exif_orientation_is_baked_into_resized_pixels() -> None:
    """
    A rotated phone photo comes out with the rotation applied.

    The re-encoded JPEG carries no EXIF, so failing to transpose first would display
    every portrait phone photo sideways on the TV.
    """
    exif = PILImage.Exif()
    exif[0x0112] = 6  # orientation: rotate 90 CW to display
    landscape_stored = _encode(PILImage.new("RGB", (4000, 2000), "red"), exif=exif)

    result = _normalize(_photo(landscape_stored))

    # Displayed as portrait (2000x4000), fitted to the box: 540x1080.
    assert (result.width, result.height) == (540, 1080)
    decoded = PILImage.open(io.BytesIO(result.data))
    assert (decoded.width, decoded.height) == (540, 1080)


def test_exif_orientation_refreshes_dimensions_on_passthrough() -> None:
    """A fitting rotated JPEG keeps its bytes but reports its *displayed* dimensions."""
    exif = PILImage.Exif()
    exif[0x0112] = 6
    data = _encode(PILImage.new("RGB", (800, 600), "red"), exif=exif)

    result = _normalize(_photo(data))

    assert result.data == data
    # Matte selection must see the portrait orientation the TV will display.
    assert (result.width, result.height) == (600, 800)


def test_png_is_reencoded_to_jpeg_even_when_it_fits() -> None:
    """Non-JPEG inputs are converted; some Frame models only accept JPEG."""
    result = _normalize(_photo(_encode(PILImage.new("RGB", (800, 600), "red"), "PNG"), ".png", "image/png"))

    assert PILImage.open(io.BytesIO(result.data)).format == "JPEG"
    assert result.file_type_suffix == ".jpg"
    assert result.content_type == "image/jpeg"


def test_rgba_input_is_flattened_for_jpeg() -> None:
    """An image with an alpha channel converts cleanly (JPEG cannot store RGBA)."""
    result = _normalize(_photo(_encode(PILImage.new("RGBA", (800, 600)), "PNG"), ".png", "image/png"))

    assert PILImage.open(io.BytesIO(result.data)).format == "JPEG"


def test_undecodable_input_falls_back_to_the_original() -> None:
    """Normalization failure must degrade to the previous behaviour, not block the push."""
    photo = _photo(b"this is not an image", ".jpg")

    assert _normalize(photo) is photo


def test_store_upload_payload_writes_and_prunes(tmp_path: Path) -> None:
    """Payload copies accumulate up to ``keep`` and the oldest are pruned."""
    keep = 3
    directory = tmp_path / "upload_debug"
    for i in range(5):
        store_upload_payload(directory, f"local:{i}", _photo(f"payload-{i}".encode()), keep=keep)

    remaining = sorted(p.name for p in directory.iterdir())
    assert len(remaining) == keep
    # The newest three survive; timestamped names keep them in chronological order.
    assert [p.split("_", 1)[1] for p in remaining] == ["local_2.jpg", "local_3.jpg", "local_4.jpg"]


def test_store_upload_payload_sanitizes_the_composite_id(tmp_path: Path) -> None:
    """Ids with separators (immich UUIDs, colons) cannot escape the directory."""
    store_upload_payload(tmp_path, "immich-1:../../etc/passwd", _photo(b"x"), keep=5)

    (payload,) = tmp_path.iterdir()
    assert payload.parent == tmp_path
    assert "/" not in payload.name


def test_store_upload_payload_never_raises(tmp_path: Path) -> None:
    """A broken destination is logged, not raised: diagnostics must not break uploads."""
    blocker = tmp_path / "blocked"
    blocker.write_text("a file where the directory should go")

    store_upload_payload(blocker, "local:1", _photo(b"x"), keep=5)  # must not raise
