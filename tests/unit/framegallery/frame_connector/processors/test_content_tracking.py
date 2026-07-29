"""
Tests for the TV content bookkeeping that prevents orphaned images.

Every image this app uploads must stay accounted for until the TV confirms it is
gone. Whenever that stops being true, images pile up on the TV that nothing can
identify or delete: tracking used to be in-memory only (lost on every restart), and
the assignment recording a new image sat *after* the select/delete calls, so any
failure in between skipped it.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from framegallery.frame_connector.processors import base
from framegallery.frame_connector.processors.sync_thread import SyncThreadProcessor
from framegallery.repository.config_repository import ConfigKey


@pytest.fixture
def stored() -> dict:
    """Return an in-memory stand-in for the persisted config values."""
    return {}


@pytest.fixture(autouse=True)
def _stub_config_io(monkeypatch, stored: dict) -> None:  # noqa: ANN001
    """Route the processor's config reads/writes through the `stored` dict."""
    monkeypatch.setattr(base, "read_bool_setting", lambda *_, **__: False)
    monkeypatch.setattr(base, "read_json_setting", lambda key, default=None: stored.get(key, default))
    monkeypatch.setattr(base, "read_str_setting", lambda key, default=None: stored.get(key, default))

    def _write(key, value) -> bool:  # noqa: ANN001
        stored[key] = value
        return True

    monkeypatch.setattr(base, "write_setting", _write)


@pytest.fixture
def processor(_stub_config_io: None) -> SyncThreadProcessor:
    """Return a connected SyncThreadProcessor with a mocked sync art client."""
    with patch("framegallery.frame_connector.processors.base.asyncio.create_task"):
        proc = SyncThreadProcessor("192.168.1.100", 8002)
    proc._connected = True  # noqa: SLF001
    proc._tv_is_online = True  # noqa: SLF001
    proc._art = MagicMock()  # noqa: SLF001
    proc._last_used = time.monotonic()  # noqa: SLF001
    return proc


# --- recording an upload ---


def test_recording_an_upload_queues_the_previous_image(processor: SyncThreadProcessor) -> None:
    """The image being replaced becomes the one we owe the TV a delete for."""
    processor._latest_content_id = "MY-OLD"  # noqa: SLF001

    processor.record_uploaded("MY-NEW")

    assert processor._latest_content_id == "MY-NEW"  # noqa: SLF001
    assert processor._pending_deletions == ["MY-OLD"]  # noqa: SLF001


def test_first_upload_queues_nothing(processor: SyncThreadProcessor) -> None:
    """With no previous image there is nothing to delete."""
    processor.record_uploaded("MY-NEW")

    assert processor._latest_content_id == "MY-NEW"  # noqa: SLF001
    assert processor._pending_deletions == []  # noqa: SLF001


def test_re_recording_the_same_id_does_not_queue_it(processor: SyncThreadProcessor) -> None:
    """Re-recording the current image must not schedule the displayed image for deletion."""
    processor.record_uploaded("MY-NEW")
    processor.record_uploaded("MY-NEW")

    assert processor._latest_content_id == "MY-NEW"  # noqa: SLF001
    assert processor._pending_deletions == []  # noqa: SLF001


def test_tracking_is_persisted(processor: SyncThreadProcessor, stored: dict) -> None:
    """Bookkeeping is written through, so a restart does not abandon the images."""
    processor._latest_content_id = "MY-OLD"  # noqa: SLF001

    processor.record_uploaded("MY-NEW")

    assert stored[ConfigKey.LATEST_TV_CONTENT_ID] == "MY-NEW"
    assert stored[ConfigKey.PENDING_TV_DELETIONS] == ["MY-OLD"]


def test_tracking_survives_a_restart(processor: SyncThreadProcessor) -> None:
    """
    A fresh processor picks up where the previous one left off.

    This is the fix for the dominant leak: whichever image was live at restart time
    used to be forgotten, leaving it on the TV with nothing able to delete it.
    """
    processor._latest_content_id = "MY-OLD"  # noqa: SLF001
    processor.record_uploaded("MY-NEW")

    with patch("framegallery.frame_connector.processors.base.asyncio.create_task"):
        restarted = SyncThreadProcessor("192.168.1.100", 8002)

    assert restarted._latest_content_id == "MY-NEW"  # noqa: SLF001
    assert restarted._pending_deletions == ["MY-OLD"]  # noqa: SLF001


def test_corrupt_pending_list_is_ignored(monkeypatch, stored: dict) -> None:  # noqa: ANN001, ARG001
    """Garbage in the config table must not stop the processor from starting."""

    def _read(key, default=None):  # noqa: ANN001, ANN202
        return "not-a-list" if key is ConfigKey.PENDING_TV_DELETIONS else default

    monkeypatch.setattr(base, "read_json_setting", _read)

    with patch("framegallery.frame_connector.processors.base.asyncio.create_task"):
        proc = SyncThreadProcessor("192.168.1.100", 8002)

    assert proc._pending_deletions == []  # noqa: SLF001


# --- draining ---


@pytest.mark.asyncio
async def test_drain_deletes_in_one_batched_call(processor: SyncThreadProcessor) -> None:
    """
    All outstanding ids go in a single delete_list call.

    One command instead of N: every extra command is another chance to wedge the
    Frame, and a wedged Frame is precisely what leaves images behind.
    """
    processor._settle = AsyncMock()  # noqa: SLF001
    processor._pending_deletions = ["A", "B", "C"]  # noqa: SLF001
    processor.delete_files = AsyncMock(return_value={"A": True, "B": True, "C": True})

    await processor.drain_pending_deletions()

    processor.delete_files.assert_awaited_once_with(["A", "B", "C"])
    assert processor._pending_deletions == []  # noqa: SLF001


@pytest.mark.asyncio
async def test_drain_with_nothing_queued_touches_neither_tv_nor_clock(processor: SyncThreadProcessor) -> None:
    """
    An empty queue costs nothing -- no TV call and no settle.

    tv_command_delay is measured in seconds, so pausing before a no-op would add
    that delay to every slideshow tick.
    """
    processor._settle = AsyncMock()  # noqa: SLF001
    processor.delete_files = AsyncMock()

    await processor.drain_pending_deletions()

    processor.delete_files.assert_not_awaited()
    processor._settle.assert_not_awaited()  # noqa: SLF001


@pytest.mark.asyncio
async def test_failed_deletes_stay_queued_for_the_next_cycle(processor: SyncThreadProcessor) -> None:
    """A partial failure retries rather than orphaning: only confirmed ids are dropped."""
    processor._settle = AsyncMock()  # noqa: SLF001
    processor._pending_deletions = ["A", "B"]  # noqa: SLF001
    processor.delete_files = AsyncMock(return_value={"A": True, "B": False})

    await processor.drain_pending_deletions()

    assert processor._pending_deletions == ["B"]  # noqa: SLF001


@pytest.mark.asyncio
async def test_unavailable_tv_keeps_everything_queued(processor: SyncThreadProcessor) -> None:
    """delete_files returning None means the TV was unreachable, not that ids are gone."""
    processor._settle = AsyncMock()  # noqa: SLF001
    processor._pending_deletions = ["A", "B"]  # noqa: SLF001
    processor.delete_files = AsyncMock(return_value=None)

    await processor.drain_pending_deletions()

    assert processor._pending_deletions == ["A", "B"]  # noqa: SLF001


@pytest.mark.asyncio
async def test_a_raising_delete_keeps_everything_queued(processor: SyncThreadProcessor) -> None:
    """An exception mid-drain must not silently drop the backlog."""
    processor._settle = AsyncMock()  # noqa: SLF001
    processor._pending_deletions = ["A"]  # noqa: SLF001
    processor.delete_files = AsyncMock(side_effect=OSError("socket gone"))

    await processor.drain_pending_deletions()

    assert processor._pending_deletions == ["A"]  # noqa: SLF001


@pytest.mark.asyncio
async def test_drain_is_capped_per_cycle(processor: SyncThreadProcessor) -> None:
    """A large backlog is worked through in bounded batches rather than one huge call."""
    processor._settle = AsyncMock()  # noqa: SLF001
    queued = [f"ID-{i}" for i in range(processor.PENDING_DELETION_BATCH + 5)]
    processor._pending_deletions = list(queued)  # noqa: SLF001
    processor.delete_files = AsyncMock(side_effect=lambda ids: dict.fromkeys(ids, True))

    await processor.drain_pending_deletions()

    processor.delete_files.assert_awaited_once_with(queued[: processor.PENDING_DELETION_BATCH])
    assert processor._pending_deletions == queued[processor.PENDING_DELETION_BATCH :]  # noqa: SLF001


def test_pending_list_is_bounded(processor: SyncThreadProcessor) -> None:
    """The backlog cannot grow without bound if deletes keep failing."""
    for i in range(processor.MAX_PENDING_DELETIONS + 10):
        processor._queue_for_deletion(f"ID-{i}")  # noqa: SLF001

    assert len(processor._pending_deletions) == processor.MAX_PENDING_DELETIONS  # noqa: SLF001
    # The newest are kept; the oldest fall through to the auto-cleanup sweep.
    assert processor._pending_deletions[-1] == f"ID-{processor.MAX_PENDING_DELETIONS + 9}"  # noqa: SLF001


# --- the hot path keeps everything accounted for ---


async def _run_apply(processor: SyncThreadProcessor, *, select_fails: bool = False) -> list[str]:
    """Drive apply_active_image with a stubbed TV, returning the ops issued."""
    photo = MagicMock(composite_id="local:1")
    photo_bytes = MagicMock(data=b"x", file_type_suffix="jpg", width=1920, height=1080)
    processor._fetch_photo_bytes = AsyncMock(return_value=photo_bytes)  # noqa: SLF001
    processor._settle = AsyncMock()  # noqa: SLF001
    processor.verify_art_mode_after_write = AsyncMock()

    calls: list[str] = []

    async def fake_run(fn, *, description, timeout, max_attempts=None):  # noqa: ANN001, ANN202, ARG001, ASYNC109
        calls.append(description)
        if description.startswith("upload"):
            return "MY-NEW"
        if select_fails and description.startswith("select"):
            msg = "TV rejected the switch"
            raise OSError(msg)
        return None

    processor._run_tv_op = fake_run  # noqa: SLF001
    await processor.apply_active_image(photo)
    return calls


@pytest.mark.asyncio
async def test_a_failed_select_still_tracks_the_new_image(processor: SyncThreadProcessor) -> None:
    """
    The new image is recorded even when activating it fails.

    Previously the assignment sat after select/delete, so this path left the image on
    the TV with nothing tracking it -- an orphan per failed activation.
    """
    processor._latest_content_id = "MY-OLD"  # noqa: SLF001

    await _run_apply(processor, select_fails=True)

    assert processor._latest_content_id == "MY-NEW"  # noqa: SLF001


@pytest.mark.asyncio
async def test_uploads_are_not_retried(processor: SyncThreadProcessor) -> None:
    """
    The upload runs with a single attempt.

    upload() streams the whole image and only then waits for the reply, so a timeout
    usually means the TV kept it. Retrying re-sends, turning one failed cycle into up
    to three untracked copies.
    """
    seen: dict[str, int | None] = {}

    async def fake_run(fn, *, description, timeout, max_attempts=None):  # noqa: ANN001, ANN202, ARG001, ASYNC109
        seen[description.split()[0]] = max_attempts
        return "MY-NEW" if description.startswith("upload") else None

    processor._fetch_photo_bytes = AsyncMock(  # noqa: SLF001
        return_value=MagicMock(data=b"x", file_type_suffix="jpg", width=1920, height=1080)
    )
    processor._settle = AsyncMock()  # noqa: SLF001
    processor.verify_art_mode_after_write = AsyncMock()
    processor._run_tv_op = fake_run  # noqa: SLF001

    await processor.apply_active_image(MagicMock(composite_id="local:1"))

    assert seen["upload"] == 1
    # Activating is safe to retry, so it keeps the default budget.
    assert seen["select"] is None
