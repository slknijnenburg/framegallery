"""Tests for the shared upload-payload preparation in UploadProcessor._fetch_photo_bytes."""

import io
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image as PILImage

from framegallery.frame_connector.processors import base
from framegallery.frame_connector.processors.sync_thread import SyncThreadProcessor
from framegallery.libraries.base import PhotoBytes

_CREATE_TASK = "framegallery.frame_connector.processors.base.asyncio.create_task"


@pytest.fixture(autouse=True)
def _stub_config_io(monkeypatch) -> None:  # noqa: ANN001
    """Answer the processor's config reads/writes without touching a real database."""
    monkeypatch.setattr(base, "read_bool_setting", lambda *_, **__: False)
    monkeypatch.setattr(base, "read_json_setting", lambda _key, default=None: default)
    monkeypatch.setattr(base, "read_str_setting", lambda _key, default=None: default)
    monkeypatch.setattr(base, "write_setting", lambda *_, **__: True)


def _oversized_png_photo() -> PhotoBytes:
    buffer = io.BytesIO()
    PILImage.new("RGB", (4000, 3000), "red").save(buffer, format="PNG")
    return PhotoBytes(data=buffer.getvalue(), content_type="image/png", file_type_suffix=".png")


def _processor() -> SyncThreadProcessor:
    with patch(_CREATE_TASK):
        proc = SyncThreadProcessor("192.168.1.100", 8002)
    proc.library_manager = SimpleNamespace(fetch_bytes=AsyncMock(return_value=_oversized_png_photo()))
    return proc


@pytest.mark.asyncio
async def test_fetch_photo_bytes_normalizes_the_payload(monkeypatch) -> None:  # noqa: ANN001
    """Whatever a library returns, the TV is handed a fitted JPEG."""
    monkeypatch.setattr(base.settings, "upload_debug_keep", 0)
    processor = _processor()

    result = await processor._fetch_photo_bytes(SimpleNamespace(composite_id="immich-1:abc"))  # noqa: SLF001

    assert result is not None
    assert result.file_type_suffix == ".jpg"
    assert (result.width, result.height) == (1440, 1080)


@pytest.mark.asyncio
async def test_payload_copy_is_kept_when_enabled(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    """With upload_debug_keep set, the exact payload lands in {data_path}/upload_debug/."""
    monkeypatch.setattr(base.settings, "upload_debug_keep", 3)
    monkeypatch.setattr(base.settings, "data_path", str(tmp_path))
    processor = _processor()

    result = await processor._fetch_photo_bytes(SimpleNamespace(composite_id="local:7"))  # noqa: SLF001

    (payload,) = (tmp_path / "upload_debug").iterdir()
    assert payload.read_bytes() == result.data


@pytest.mark.asyncio
async def test_no_payload_copy_by_default(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    """With the default upload_debug_keep of 0, nothing is written to disk."""
    monkeypatch.setattr(base.settings, "upload_debug_keep", 0)
    monkeypatch.setattr(base.settings, "data_path", str(tmp_path))
    processor = _processor()

    await processor._fetch_photo_bytes(SimpleNamespace(composite_id="local:7"))  # noqa: SLF001

    assert not (tmp_path / "upload_debug").exists()
