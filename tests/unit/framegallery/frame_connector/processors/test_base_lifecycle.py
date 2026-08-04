"""Lifecycle tests for the shared UploadProcessor machinery (pinger + shutdown)."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from framegallery.frame_connector.processors import base
from framegallery.frame_connector.processors.single_async import SingleAsyncProcessor

_CREATE_TASK = "framegallery.frame_connector.processors.base.asyncio.create_task"


@pytest.fixture(autouse=True)
def _stub_config_io(monkeypatch) -> None:  # noqa: ANN001
    """
    Answer the processor's config reads without touching a real database.

    Construction restores the TV content bookkeeping; against an absent database that
    logs warnings, which would pollute the caplog assertions below.
    """
    monkeypatch.setattr(base, "read_bool_setting", lambda *_, **__: False)
    monkeypatch.setattr(base, "read_json_setting", lambda _key, default=None: default)
    monkeypatch.setattr(base, "read_str_setting", lambda _key, default=None: default)
    monkeypatch.setattr(base, "write_setting", lambda *_, **__: True)


def _build_processor() -> SingleAsyncProcessor:
    """Build a processor without actually starting the pinger task."""
    with patch(_CREATE_TASK):
        return SingleAsyncProcessor("192.168.1.100", 8002)


def test_start_pinger_is_idempotent_while_one_runs() -> None:
    """A second _start_reconnection_pinger is a no-op while a pinger is still running."""
    proc = _build_processor()
    proc._pinger_task = MagicMock()  # noqa: SLF001
    proc._pinger_task.done.return_value = False  # noqa: SLF001

    with patch(_CREATE_TASK) as create_task:
        proc._start_reconnection_pinger()  # noqa: SLF001
        create_task.assert_not_called()


def test_start_pinger_restarts_when_previous_finished() -> None:
    """A finished pinger can be replaced by a new one (e.g. after a disconnect)."""
    proc = _build_processor()
    proc._pinger_task = MagicMock()  # noqa: SLF001
    proc._pinger_task.done.return_value = True  # noqa: SLF001

    with patch(_CREATE_TASK) as create_task:
        proc._start_reconnection_pinger()  # noqa: SLF001
        create_task.assert_called_once()


def test_start_pinger_noop_while_shutting_down() -> None:
    """No pinger is (re)started once shutdown has begun."""
    proc = _build_processor()
    proc._shutting_down = True  # noqa: SLF001

    with patch(_CREATE_TASK) as create_task:
        proc._start_reconnection_pinger()  # noqa: SLF001
        create_task.assert_not_called()


def _log_failure(proc: SingleAsyncProcessor, exc: Exception) -> None:
    """Invoke the failure logger from a real exception context (so exc_info is set)."""
    try:
        raise exc
    except type(exc) as caught:
        proc._log_reconnect_failure(caught)  # noqa: SLF001


def test_reconnect_failure_logs_traceback_once_then_warns(caplog) -> None:  # noqa: ANN001
    """The first reconnect failure logs a traceback; identical repeats collapse to warnings."""
    proc = _build_processor()

    with caplog.at_level(logging.WARNING, logger="framegallery"):
        _log_failure(proc, OSError("boom"))
        _log_failure(proc, OSError("boom"))
        _log_failure(proc, OSError("boom"))

    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    # First occurrence -> one ERROR (with traceback); the two repeats -> WARNINGs.
    assert len(errors) == 1
    assert errors[0].exc_info is not None
    assert errors[0].exc_info[0] is OSError
    assert len(warnings) == 2  # noqa: PLR2004
    assert proc._reconnect_failures == 3  # noqa: SLF001, PLR2004


def test_reconnect_failure_new_error_logs_traceback_again(caplog) -> None:  # noqa: ANN001
    """A different error signature resets the dedup and logs a fresh traceback."""
    proc = _build_processor()

    with caplog.at_level(logging.WARNING, logger="framegallery"):
        _log_failure(proc, OSError("boom"))
        _log_failure(proc, RuntimeError("different"))

    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(errors) == 2  # noqa: PLR2004 -- each distinct error gets its own traceback


@pytest.mark.asyncio
async def test_shutdown_cancels_pinger_and_does_not_rearm() -> None:
    """shutdown() cancels background tasks, closes, and prevents the pinger re-arming."""
    proc = _build_processor()
    proc._tv = AsyncMock()  # noqa: SLF001

    async def _never() -> None:
        await asyncio.Event().wait()

    task = asyncio.create_task(_never())
    proc._background_tasks = {task}  # noqa: SLF001

    await proc.shutdown()

    assert proc._shutting_down is True  # noqa: SLF001
    assert task.cancelled()
    proc._tv.close.assert_awaited_once()  # noqa: SLF001

    # close() runs during shutdown and calls _start_reconnection_pinger, which must no-op.
    with patch(_CREATE_TASK) as create_task:
        proc._start_reconnection_pinger()  # noqa: SLF001
        create_task.assert_not_called()


# --- token pairing only applies to the secure port ---


@pytest.mark.asyncio
async def test_pairing_is_skipped_on_the_plain_websocket_port() -> None:
    """
    On the plain-WebSocket port there is no token to obtain.

    That port's art URL carries no token parameter, so pairing achieves nothing --
    and its remote-control channel rejects unauthenticated clients with
    ms.channel.unauthorized. Running pairing there would raise on every reconnect
    and leave the app permanently disconnected.
    """
    proc = _build_processor()
    proc._port = SingleAsyncProcessor.SECURE_PORT + 1  # noqa: SLF001 -- any non-secure port

    with patch("framegallery.frame_connector.processors.base.SamsungTVWSAsyncRemote") as remote_cls:
        await proc._ensure_token()  # noqa: SLF001

    remote_cls.assert_not_called()


@pytest.mark.asyncio
async def test_pairing_runs_on_the_secure_port() -> None:
    """The secure port still pairs, so the token flow is unchanged for existing setups."""
    proc = _build_processor()
    proc._port = SingleAsyncProcessor.SECURE_PORT  # noqa: SLF001

    remote = MagicMock()
    remote.open = AsyncMock()
    remote.close = AsyncMock()

    with patch(
        "framegallery.frame_connector.processors.base.SamsungTVWSAsyncRemote",
        return_value=remote,
    ) as remote_cls:
        await proc._ensure_token()  # noqa: SLF001

    remote_cls.assert_called_once()
    assert remote_cls.call_args.kwargs["port"] == SingleAsyncProcessor.SECURE_PORT
    remote.open.assert_awaited_once()
    remote.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_pairing_closes_the_remote_even_when_open_fails() -> None:
    """A failed pairing must not leak the remote-control connection."""
    proc = _build_processor()
    proc._port = SingleAsyncProcessor.SECURE_PORT  # noqa: SLF001

    remote = MagicMock()
    remote.open = AsyncMock(side_effect=OSError("refused"))
    remote.close = AsyncMock()

    with (
        patch("framegallery.frame_connector.processors.base.SamsungTVWSAsyncRemote", return_value=remote),
        pytest.raises(OSError, match="refused"),
    ):
        await proc._ensure_token()  # noqa: SLF001

    remote.close.assert_awaited_once()
