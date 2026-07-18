"""Lifecycle tests for the shared UploadProcessor machinery (pinger + shutdown)."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from framegallery.frame_connector.processors.single_async import SingleAsyncProcessor

_CREATE_TASK = "framegallery.frame_connector.processors.base.asyncio.create_task"


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
