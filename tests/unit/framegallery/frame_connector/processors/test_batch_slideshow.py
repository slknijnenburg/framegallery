"""Unit tests for the batch_slideshow upload processor."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from framegallery.auto_cleanup import tv_cleanup_service as cleanup_module
from framegallery.auto_cleanup.tv_cleanup_service import TvCleanupService
from framegallery.frame_connector.processors import batch_slideshow
from framegallery.frame_connector.processors.batch_slideshow import BatchSlideshowProcessor

EXPECTED_BATCH_SIZE = 3


def _photo_bytes() -> SimpleNamespace:
    return SimpleNamespace(data=b"x", file_type_suffix="jpg", width=1920, height=1080)


@pytest.fixture
def processor() -> BatchSlideshowProcessor:
    """Return a connected BatchSlideshowProcessor with a mocked async TV client."""
    with patch("framegallery.frame_connector.processors.base.asyncio.create_task"):
        proc = BatchSlideshowProcessor("192.168.1.100", 8002)
    proc._connected = True  # noqa: SLF001
    proc._tv_is_online = True  # noqa: SLF001
    proc._tv = AsyncMock()  # noqa: SLF001
    return proc


@pytest.mark.asyncio
async def test_refill_batch_evicts_then_uploads_unique(processor: BatchSlideshowProcessor, monkeypatch) -> None:  # noqa: ANN001
    """_refill_batch evicts existing files then uploads batch_size unique photos."""
    monkeypatch.setattr(batch_slideshow.settings, "batch_size", EXPECTED_BATCH_SIZE)

    library_manager = MagicMock()
    # Includes a duplicate (local:2) which must be de-duplicated.
    picks = [
        SimpleNamespace(composite_id="local:1"),
        SimpleNamespace(composite_id="local:2"),
        SimpleNamespace(composite_id="local:2"),
        SimpleNamespace(composite_id="local:3"),
    ]
    library_manager.pick_photo = AsyncMock(side_effect=picks)
    processor.library_manager = library_manager

    processor.list_files = AsyncMock(return_value=[{"content_id": "OLD1"}, {"content_id": "OLD2"}])
    processor.delete_files = AsyncMock()
    processor._fetch_photo_bytes = AsyncMock(return_value=_photo_bytes())  # noqa: SLF001

    upload_count = {"n": 0}

    async def fake_upload(_photo, _bytes) -> dict:  # noqa: ANN001
        upload_count["n"] += 1
        return {"content_id": f"NEW{upload_count['n']}"}

    processor._upload_photo = fake_upload  # noqa: SLF001

    await processor._refill_batch()  # noqa: SLF001

    processor.delete_files.assert_awaited_once_with(["OLD1", "OLD2"])
    assert set(processor._resident) == {"local:1", "local:2", "local:3"}  # noqa: SLF001
    assert upload_count["n"] == EXPECTED_BATCH_SIZE


@pytest.mark.asyncio
async def test_apply_active_image_uploads_when_not_resident(processor: BatchSlideshowProcessor) -> None:
    """An explicit select of a non-resident photo uploads then activates it."""
    processor._activate_image = AsyncMock()  # noqa: SLF001
    processor._fetch_photo_bytes = AsyncMock(return_value=_photo_bytes())  # noqa: SLF001
    processor._upload_photo = AsyncMock(return_value={"content_id": "NEW9"})  # noqa: SLF001

    await processor.apply_active_image(SimpleNamespace(composite_id="local:9"))

    processor._activate_image.assert_awaited_once_with("NEW9")  # noqa: SLF001
    assert processor._resident["local:9"] == "NEW9"  # noqa: SLF001


@pytest.mark.asyncio
async def test_apply_active_image_activates_resident_without_upload(processor: BatchSlideshowProcessor) -> None:
    """An explicit select of a resident photo activates it without re-uploading."""
    processor._activate_image = AsyncMock()  # noqa: SLF001
    processor._upload_photo = AsyncMock()  # noqa: SLF001
    processor._resident["local:5"] = "EXIST5"  # noqa: SLF001

    await processor.apply_active_image(SimpleNamespace(composite_id="local:5"))

    processor._activate_image.assert_awaited_once_with("EXIST5")  # noqa: SLF001
    processor._upload_photo.assert_not_called()  # noqa: SLF001


@pytest.mark.asyncio
async def test_enable_tv_rotation_sets_shuffle(processor: BatchSlideshowProcessor, monkeypatch) -> None:  # noqa: ANN001
    """_enable_tv_rotation turns on the TV's shuffle rotation with the configured interval."""
    monkeypatch.setattr(batch_slideshow.settings, "batch_rotation_minutes", 5)
    processor._tv.get_auto_rotation_status = AsyncMock(return_value={"value": "5"})  # noqa: SLF001

    with patch.object(batch_slideshow.asyncio, "sleep", new=AsyncMock()):
        await processor._enable_tv_rotation()  # noqa: SLF001

    processor._tv.set_auto_rotation_status.assert_awaited_once_with(duration=5, type=True, category=2)  # noqa: SLF001
    processor._tv.set_slideshow_status.assert_awaited_once_with(duration=5, type=True, category=2)  # noqa: SLF001


@pytest.mark.asyncio
async def test_enable_tv_rotation_retries_transient_failure(processor: BatchSlideshowProcessor) -> None:
    """A transient timeout on the enable call (AssertionError) is retried, not fatal."""
    # First attempt raises (mirrors samsungtvws' `assert data` on a timed-out request),
    # second attempt succeeds.
    processor._tv.set_auto_rotation_status = AsyncMock(side_effect=[AssertionError, None])  # noqa: SLF001
    processor._tv.set_slideshow_status = AsyncMock(return_value=None)  # noqa: SLF001
    processor._tv.get_auto_rotation_status = AsyncMock(return_value={"value": "3"})  # noqa: SLF001

    with patch.object(batch_slideshow.asyncio, "sleep", new=AsyncMock()):
        await processor._enable_tv_rotation()  # noqa: SLF001

    assert processor._tv.set_auto_rotation_status.await_count == 2  # noqa: SLF001, PLR2004


@pytest.mark.asyncio
async def test_enable_rotation_call_gives_up_after_max_attempts(processor: BatchSlideshowProcessor) -> None:
    """_enable_rotation_call returns False after exhausting all attempts."""
    always_fails = AsyncMock(side_effect=AssertionError)

    with patch.object(batch_slideshow.asyncio, "sleep", new=AsyncMock()):
        ok = await processor._enable_rotation_call("set_auto_rotation_status", always_fails)  # noqa: SLF001

    assert ok is False
    assert always_fails.await_count == batch_slideshow._ROTATION_ATTEMPTS  # noqa: SLF001


def test_cleanup_disabled_in_batch_mode(monkeypatch) -> None:  # noqa: ANN001
    """Auto-cleanup is force-disabled while the batch_slideshow processor is active."""
    monkeypatch.setattr(cleanup_module.settings, "upload_processor", "batch_slideshow")
    config_repo = MagicMock()
    config_repo.get_bool.return_value = True  # even if the flag says enabled...

    service = TvCleanupService(MagicMock(), config_repo)

    assert service._is_cleanup_enabled() is False  # noqa: SLF001
    config_repo.get_bool.assert_not_called()  # batch short-circuits before reading config
