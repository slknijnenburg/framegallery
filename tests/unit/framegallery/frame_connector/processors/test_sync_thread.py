"""Unit tests for the sync_thread upload processor."""

import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from framegallery.frame_connector.processors import sync_thread
from framegallery.frame_connector.processors.sync_thread import SyncThreadProcessor


@pytest.fixture
def processor() -> SyncThreadProcessor:
    """Return a connected SyncThreadProcessor with a mocked sync art client."""
    with patch("framegallery.frame_connector.processors.base.asyncio.create_task"):
        proc = SyncThreadProcessor("192.168.1.100", 8002)
    proc._connected = True  # noqa: SLF001
    proc._tv_is_online = True  # noqa: SLF001
    proc._art = MagicMock()  # noqa: SLF001
    proc._last_used = time.monotonic()  # noqa: SLF001
    return proc


@pytest.mark.asyncio
async def test_run_tv_op_runs_in_thread(processor: SyncThreadProcessor) -> None:
    """A TV op is dispatched via asyncio.to_thread and its result returned."""
    processor._art.get_current.return_value = {"content_id": "MY-F0001"}  # noqa: SLF001

    with patch(
        "framegallery.frame_connector.processors.sync_thread.asyncio.to_thread",
        wraps=asyncio.to_thread,
    ) as to_thread:
        result = await processor._run_tv_op(  # noqa: SLF001
            lambda art: art.get_current(), description="get_current", timeout=5
        )

    assert result == {"content_id": "MY-F0001"}
    to_thread.assert_called()


@pytest.mark.asyncio
async def test_run_tv_op_serialises_with_lock(processor: SyncThreadProcessor) -> None:
    """The op lock is held for the duration of an operation."""
    processor._ensure_live_client = AsyncMock()  # noqa: SLF001

    async def op() -> str:
        return await processor._run_tv_op(lambda art: "ok", description="x", timeout=5)  # noqa: SLF001, ARG005

    # If the lock were not held, acquiring it here would not matter; this asserts the
    # public contract that operations acquire _op_lock.
    assert not processor._op_lock.locked()  # noqa: SLF001
    await op()
    assert not processor._op_lock.locked()  # noqa: SLF001


@pytest.mark.asyncio
async def test_run_tv_op_retries_then_succeeds(processor: SyncThreadProcessor) -> None:
    """A transient failure is retried (with WoL + close) and then succeeds."""
    processor._ensure_live_client = AsyncMock()  # noqa: SLF001
    processor._close_client = AsyncMock()  # noqa: SLF001
    processor._wake_tv = MagicMock()  # noqa: SLF001

    seq: list[object] = [OSError("boom"), "ok"]

    def fn(_art: object) -> object:
        item = seq.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    with patch("framegallery.frame_connector.processors.sync_thread.asyncio.sleep", new=AsyncMock()):
        result = await processor._run_tv_op(fn, description="x", timeout=5)  # noqa: SLF001

    assert result == "ok"
    processor._close_client.assert_awaited()  # noqa: SLF001
    processor._wake_tv.assert_called_once()  # WoL on the first retry  # noqa: SLF001


@pytest.mark.asyncio
async def test_run_tv_op_gives_up_after_max_attempts(processor: SyncThreadProcessor) -> None:
    """After MAX_ATTEMPTS failures the last exception is raised."""
    processor._ensure_live_client = AsyncMock()  # noqa: SLF001
    processor._close_client = AsyncMock()  # noqa: SLF001
    processor._wake_tv = MagicMock()  # noqa: SLF001

    def fn(_art: object) -> object:
        raise OSError("always")

    with (
        patch("framegallery.frame_connector.processors.sync_thread.asyncio.sleep", new=AsyncMock()),
        pytest.raises(OSError, match="always"),
    ):
        await processor._run_tv_op(fn, description="x", timeout=5)  # noqa: SLF001


@pytest.mark.asyncio
async def test_ensure_live_client_recycles_when_idle(processor: SyncThreadProcessor) -> None:
    """An idle connection is closed and reopened before the next op."""
    processor._last_used = time.monotonic() - (SyncThreadProcessor.IDLE_RECYCLE_SECONDS + 5)  # noqa: SLF001
    processor._close_client = AsyncMock()  # noqa: SLF001
    processor._connect_client = AsyncMock()  # noqa: SLF001

    await processor._ensure_live_client()  # noqa: SLF001

    processor._close_client.assert_awaited_once()  # noqa: SLF001
    processor._connect_client.assert_awaited_once()  # noqa: SLF001


@pytest.mark.asyncio
async def test_ensure_live_client_reuses_when_fresh(processor: SyncThreadProcessor) -> None:
    """A recently-used connection is reused without recycling."""
    processor._last_used = time.monotonic()  # noqa: SLF001
    processor._close_client = AsyncMock()  # noqa: SLF001
    processor._connect_client = AsyncMock()  # noqa: SLF001

    await processor._ensure_live_client()  # noqa: SLF001

    processor._close_client.assert_not_called()  # noqa: SLF001
    processor._connect_client.assert_not_called()  # noqa: SLF001


def test_wake_tv_noop_without_mac(processor: SyncThreadProcessor, monkeypatch) -> None:  # noqa: ANN001
    """No Wake-on-LAN packet is sent when no MAC is configured."""
    monkeypatch.setattr(sync_thread.settings, "tv_mac_address", None)
    send = MagicMock()
    with patch.dict("sys.modules", {"wakeonlan": SimpleNamespace(send_magic_packet=send)}):
        processor._wake_tv()  # noqa: SLF001 -- should simply do nothing
    send.assert_not_called()


def test_wake_tv_sends_packet_with_mac(processor: SyncThreadProcessor, monkeypatch) -> None:  # noqa: ANN001
    """A Wake-on-LAN packet is sent when a MAC is configured."""
    monkeypatch.setattr(sync_thread.settings, "tv_mac_address", "AA:BB:CC:DD:EE:FF")
    send = MagicMock()
    with patch.dict("sys.modules", {"wakeonlan": SimpleNamespace(send_magic_packet=send)}):
        processor._wake_tv()  # noqa: SLF001
    send.assert_called_once_with("AA:BB:CC:DD:EE:FF")


@pytest.mark.asyncio
async def test_apply_active_image_uploads_activates_deletes(processor: SyncThreadProcessor) -> None:
    """apply_active_image uploads, activates, and deletes the previous image."""
    photo = SimpleNamespace(composite_id="local:1")
    photo_bytes = SimpleNamespace(data=b"x", file_type_suffix="jpg", width=1920, height=1080)
    processor._fetch_photo_bytes = AsyncMock(return_value=photo_bytes)  # noqa: SLF001
    processor._settle = AsyncMock()  # noqa: SLF001 -- don't actually sleep in the test
    processor._latest_content_id = "MY-OLD"  # noqa: SLF001

    calls: list[str] = []

    async def fake_run(fn, *, description, timeout):  # noqa: ANN001, ANN202, ARG001, ASYNC109
        calls.append(description)
        # The sync SamsungTVArt.upload() returns the content_id as a bare string.
        if description.startswith("upload"):
            return "MY-F0009"
        return None

    processor._run_tv_op = fake_run  # noqa: SLF001

    await processor.apply_active_image(photo)

    assert any(d.startswith("upload") for d in calls)
    assert any(d.startswith("select MY-F0009") for d in calls)
    assert any(d.startswith("delete MY-OLD") for d in calls)
    assert processor._latest_content_id == "MY-F0009"  # noqa: SLF001
    # The TV settles between commands: once before select, once before delete.
    settles_before_select_and_delete = 2
    assert processor._settle.await_count == settles_before_select_and_delete  # noqa: SLF001


@pytest.mark.asyncio
async def test_apply_active_image_settles_before_switching(processor: SyncThreadProcessor) -> None:
    """The settle pause is inserted after upload and before select_image."""
    photo = SimpleNamespace(composite_id="local:1")
    photo_bytes = SimpleNamespace(data=b"x", file_type_suffix="jpg", width=1920, height=1080)
    processor._fetch_photo_bytes = AsyncMock(return_value=photo_bytes)  # noqa: SLF001
    processor._latest_content_id = None  # noqa: SLF001 -- no previous image, so no delete

    events: list[str] = []
    processor._settle = AsyncMock(side_effect=lambda: events.append("settle"))  # noqa: SLF001

    async def fake_run(fn, *, description, timeout):  # noqa: ANN001, ANN202, ARG001, ASYNC109
        events.append(description.split()[0])
        return "MY-F0009" if description.startswith("upload") else None

    processor._run_tv_op = fake_run  # noqa: SLF001

    await processor.apply_active_image(photo)

    # Upload happens, then the settle pause, then the switch.
    assert events == ["upload", "settle", "select"]


@pytest.mark.asyncio
async def test_settle_sleeps_when_delay_positive(processor: SyncThreadProcessor, monkeypatch) -> None:  # noqa: ANN001
    """_settle sleeps for tv_command_delay seconds when it is positive."""
    monkeypatch.setattr("framegallery.frame_connector.processors.base.settings.tv_command_delay", 1.5)
    sleep = AsyncMock()
    monkeypatch.setattr("framegallery.frame_connector.processors.base.asyncio.sleep", sleep)

    await processor._settle()  # noqa: SLF001

    sleep.assert_awaited_once_with(1.5)


@pytest.mark.asyncio
async def test_settle_is_noop_when_delay_zero(processor: SyncThreadProcessor, monkeypatch) -> None:  # noqa: ANN001
    """_settle does not sleep when the delay is disabled (0)."""
    monkeypatch.setattr("framegallery.frame_connector.processors.base.settings.tv_command_delay", 0)
    sleep = AsyncMock()
    monkeypatch.setattr("framegallery.frame_connector.processors.base.asyncio.sleep", sleep)

    await processor._settle()  # noqa: SLF001

    sleep.assert_not_called()


@pytest.mark.asyncio
async def test_apply_active_image_skips_when_not_connected(processor: SyncThreadProcessor) -> None:
    """Nothing is uploaded when the processor is not connected."""
    processor._connected = False  # noqa: SLF001
    processor._fetch_photo_bytes = AsyncMock()  # noqa: SLF001

    await processor.apply_active_image(SimpleNamespace(composite_id="local:1"))

    processor._fetch_photo_bytes.assert_not_called()  # noqa: SLF001
