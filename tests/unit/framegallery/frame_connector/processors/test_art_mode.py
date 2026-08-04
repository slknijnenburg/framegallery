"""Tests for the shared art-mode helpers on UploadProcessor."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from framegallery.frame_connector.processors import base
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


@pytest.fixture(autouse=True)
def _tv_watch_mode_off(monkeypatch) -> None:  # noqa: ANN001
    """Turn TV watch mode off by default; the watch-mode tests override it."""
    monkeypatch.setattr(base, "read_bool_setting", lambda *_, **__: False)
    monkeypatch.setattr(base, "read_json_setting", lambda _key, default=None: default)
    monkeypatch.setattr(base, "read_str_setting", lambda _key, default=None: default)
    monkeypatch.setattr(base, "write_setting", lambda *_, **__: True)


def _enable_tv_watch_mode(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(base, "read_bool_setting", lambda *_, **__: True)


# --- gating ---


def test_upload_permitted_before_anything_is_known(processor: SyncThreadProcessor) -> None:
    """An unknown art-mode state stays permissive, so a watchdog problem can't freeze the slideshow."""
    assert processor.art_mode_active is None
    assert processor.art_mode_permits_upload() is True


def test_upload_permitted_when_art_mode_is_on(processor: SyncThreadProcessor) -> None:
    """The normal case."""
    processor.note_art_mode(active=True)
    assert processor.art_mode_permits_upload() is True


def test_upload_suppressed_only_by_a_confident_off(processor: SyncThreadProcessor) -> None:
    """Only a known "off" suppresses the push; uploads are invisible on regular TV."""
    processor.note_art_mode(active=False)
    assert processor.art_mode_permits_upload() is False


def test_unknown_after_a_failed_query_is_permissive(processor: SyncThreadProcessor) -> None:
    """A failed query reverts to permissive rather than latching the last "off"."""
    processor.note_art_mode(active=False)
    processor.note_art_mode(active=None)
    assert processor.art_mode_permits_upload() is True


# --- TV watch mode ---


def test_tv_watch_mode_blocks_uploads_even_in_art_mode(processor: SyncThreadProcessor, monkeypatch) -> None:  # noqa: ANN001
    """
    TV watch mode is a hard stop, independent of what art mode reports.

    Checked before the art-mode state precisely so the toggle does not depend on
    detection being accurate or up to date.
    """
    processor.note_art_mode(active=True)
    _enable_tv_watch_mode(monkeypatch)

    assert processor.art_mode_permits_upload() is False


def test_tv_watch_mode_blocks_uploads_when_state_is_unknown(processor: SyncThreadProcessor, monkeypatch) -> None:  # noqa: ANN001
    """The usual permissive fallback for an unknown state does not override the toggle."""
    processor.note_art_mode(active=None)
    _enable_tv_watch_mode(monkeypatch)

    assert processor.art_mode_permits_upload() is False


@pytest.mark.asyncio
async def test_tv_watch_mode_suppresses_the_post_write_restore(
    processor: SyncThreadProcessor,
    monkeypatch,  # noqa: ANN001
) -> None:
    """
    Art mode is not restored while watching, even though we know we caused the drop.

    This is the one place the app would otherwise be certain it should intervene; the
    toggle deliberately outranks that certainty.
    """
    processor.get_art_mode = AsyncMock(return_value=False)
    processor.set_art_mode = AsyncMock(return_value=True)
    _enable_tv_watch_mode(monkeypatch)

    await processor.verify_art_mode_after_write()

    processor.set_art_mode.assert_not_awaited()
    assert processor.art_mode_active is False


# --- post-write verification ---


@pytest.mark.asyncio
async def test_no_restore_when_art_mode_survived(processor: SyncThreadProcessor) -> None:
    """The common case: our writes did not knock the TV out of art mode."""
    processor.get_art_mode = AsyncMock(return_value=True)
    processor.set_art_mode = AsyncMock(return_value=True)

    await processor.verify_art_mode_after_write()

    processor.set_art_mode.assert_not_awaited()
    assert processor.art_mode_active is True


@pytest.mark.asyncio
async def test_restore_when_art_mode_dropped_during_our_writes(processor: SyncThreadProcessor) -> None:
    """
    Art mode off immediately after our command sequence means we caused it.

    This is the only path allowed to force art mode back on.
    """
    processor.get_art_mode = AsyncMock(side_effect=[False, True])
    processor.set_art_mode = AsyncMock(return_value=True)

    await processor.verify_art_mode_after_write()

    processor.set_art_mode.assert_awaited_once_with(enabled=True)
    assert processor.art_mode_active is True


@pytest.mark.asyncio
async def test_no_restore_attempt_when_state_is_unknown(processor: SyncThreadProcessor) -> None:
    """
    An unanswerable query must not trigger a restore.

    "Could not ask" usually means the art channel is wedged, and firing more commands
    at a Frame in that state is what the settle delays exist to avoid.
    """
    processor.get_art_mode = AsyncMock(return_value=None)
    processor.set_art_mode = AsyncMock(return_value=True)

    await processor.verify_art_mode_after_write()

    processor.set_art_mode.assert_not_awaited()
    assert processor.art_mode_active is None


@pytest.mark.asyncio
async def test_accepted_but_ineffective_restore_is_not_reported_as_success(
    processor: SyncThreadProcessor,
) -> None:
    """
    The TV accepting set_artmode is not the same as it acting on it.

    A Frame wedged badly enough to ignore the command must not be left recorded as
    being in art mode, or the slideshow would resume pushing into regular TV.
    """
    processor.get_art_mode = AsyncMock(side_effect=[False, False])
    processor.set_art_mode = AsyncMock(return_value=True)

    await processor.verify_art_mode_after_write()

    processor.set_art_mode.assert_awaited_once_with(enabled=True)
    assert processor.art_mode_active is False


@pytest.mark.asyncio
async def test_failed_restore_command_leaves_state_off(processor: SyncThreadProcessor) -> None:
    """When the command itself fails there is nothing to re-query."""
    processor.get_art_mode = AsyncMock(return_value=False)
    processor.set_art_mode = AsyncMock(return_value=False)

    await processor.verify_art_mode_after_write()

    assert processor.art_mode_active is False
    assert processor.get_art_mode.await_count == 1


# --- sync_thread's art-mode queries ---


@pytest.mark.asyncio
async def test_get_art_mode_maps_on_to_true(processor: SyncThreadProcessor) -> None:
    """The TV reports art mode as the string "on"/"off"."""
    processor._run_tv_op = AsyncMock(return_value="on")  # noqa: SLF001
    assert await processor.get_art_mode() is True

    processor._run_tv_op = AsyncMock(return_value="off")  # noqa: SLF001
    assert await processor.get_art_mode() is False


@pytest.mark.asyncio
async def test_exhausted_retries_report_unknown_not_off(processor: SyncThreadProcessor) -> None:
    """
    _run_tv_op yields None when it gives up without raising.

    That is "no answer", not "art mode is off" -- reporting False would gate the
    slideshow off and trigger a spurious restore.
    """
    processor._run_tv_op = AsyncMock(return_value=None)  # noqa: SLF001

    assert await processor.get_art_mode() is None


@pytest.mark.asyncio
async def test_query_failure_reports_unknown(processor: SyncThreadProcessor) -> None:
    """A raising query is unknown, not off."""
    processor._run_tv_op = AsyncMock(side_effect=OSError("socket gone"))  # noqa: SLF001

    assert await processor.get_art_mode() is None


@pytest.mark.asyncio
async def test_art_mode_queries_are_skipped_while_disconnected(processor: SyncThreadProcessor) -> None:
    """Without a connection there is nothing to ask, and nothing to command."""
    processor._connected = False  # noqa: SLF001
    processor._run_tv_op = AsyncMock()  # noqa: SLF001

    assert await processor.get_art_mode() is None
    assert await processor.set_art_mode(enabled=True) is False
    processor._run_tv_op.assert_not_awaited()  # noqa: SLF001


# --- the art-mode check must survive every failure path ---
#
# A Frame that dies mid-upload closes the WebSocket abruptly ("Invalid close opcode
# 1005") and reappears moments later in regular TV mode. That failed upload is the
# strongest evidence available that *we* caused the drop -- the one condition under
# which restoring art mode is unambiguously right. apply_active_image used to return
# early on it, skipping the check entirely, so the Frame sat on regular TV until
# someone noticed.


async def _apply(processor: SyncThreadProcessor, *, upload: object) -> MagicMock:
    """Drive apply_active_image with a stubbed TV; return the verification spy."""
    processor._fetch_photo_bytes = AsyncMock(  # noqa: SLF001
        return_value=MagicMock(data=b"x", file_type_suffix="jpg", width=1920, height=1080)
    )
    processor._settle = AsyncMock()  # noqa: SLF001
    verify = AsyncMock()
    processor.verify_art_mode_after_write = verify

    async def fake_run(fn, *, description, timeout, max_attempts=None):  # noqa: ANN001, ANN202, ARG001, ASYNC109
        if description.startswith("upload"):
            if isinstance(upload, Exception):
                raise upload
            return upload
        return None

    processor._run_tv_op = fake_run  # noqa: SLF001
    processor.delete_files = AsyncMock(return_value={})
    await processor.apply_active_image(MagicMock(composite_id="local:1"))
    return verify


@pytest.mark.asyncio
async def test_art_mode_is_checked_after_a_failed_upload(processor: SyncThreadProcessor) -> None:
    """A raising upload -- the Frame slamming the socket shut -- still triggers the check."""
    verify = await _apply(processor, upload=OSError("Invalid close opcode 1005"))

    verify.assert_awaited_once()


@pytest.mark.asyncio
async def test_art_mode_is_checked_when_upload_returns_no_content_id(processor: SyncThreadProcessor) -> None:
    """An upload that yields nothing may still have reached the TV."""
    verify = await _apply(processor, upload=None)

    verify.assert_awaited_once()


@pytest.mark.asyncio
async def test_art_mode_is_checked_after_a_successful_upload(processor: SyncThreadProcessor) -> None:
    """The happy path keeps checking, as before."""
    verify = await _apply(processor, upload="MY-NEW")

    verify.assert_awaited_once()


@pytest.mark.asyncio
async def test_no_check_when_the_photo_could_not_be_fetched(processor: SyncThreadProcessor) -> None:
    """Failing before any TV call means there is nothing to re-check."""
    processor._fetch_photo_bytes = AsyncMock(return_value=None)  # noqa: SLF001
    processor._settle = AsyncMock()  # noqa: SLF001
    processor.verify_art_mode_after_write = AsyncMock()

    await processor.apply_active_image(MagicMock(composite_id="local:1"))

    processor.verify_art_mode_after_write.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_check_when_the_push_was_gated_off(processor: SyncThreadProcessor) -> None:
    """A push suppressed because art mode is already off must not re-check or restore."""
    processor.note_art_mode(active=False)
    processor._settle = AsyncMock()  # noqa: SLF001
    processor.verify_art_mode_after_write = AsyncMock()
    processor._fetch_photo_bytes = AsyncMock()  # noqa: SLF001

    await processor.apply_active_image(MagicMock(composite_id="local:1"))

    processor.verify_art_mode_after_write.assert_not_awaited()
    processor._fetch_photo_bytes.assert_not_awaited()  # noqa: SLF001


@pytest.mark.asyncio
async def test_failed_upload_restores_art_mode_when_the_tv_dropped_out(processor: SyncThreadProcessor) -> None:
    """
    End to end: the exact sequence observed in production.

    Upload dies with the TV closing the socket, art mode reads back "off", and the
    restore fires -- rather than the drop being left for the periodic watchdog, which
    cannot distinguish it from someone reaching for the remote and so leaves it alone.
    """
    processor._fetch_photo_bytes = AsyncMock(  # noqa: SLF001
        return_value=MagicMock(data=b"x", file_type_suffix="jpg", width=1920, height=1080)
    )
    processor._settle = AsyncMock()  # noqa: SLF001
    processor.get_art_mode = AsyncMock(side_effect=[False, True])
    processor.set_art_mode = AsyncMock(return_value=True)

    async def fake_run(fn, *, description, timeout, max_attempts=None):  # noqa: ANN001, ANN202, ARG001, ASYNC109
        if description.startswith("upload"):
            msg = "Invalid close opcode 1005"
            raise OSError(msg)

    processor._run_tv_op = fake_run  # noqa: SLF001

    await processor.apply_active_image(MagicMock(composite_id="local:1"))

    processor.set_art_mode.assert_awaited_once_with(enabled=True)
    assert processor.art_mode_active is True
