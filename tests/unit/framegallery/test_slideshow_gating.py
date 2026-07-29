"""Tests for the periodic slideshow-tick gating (GAP 1: SLIDESHOW_ENABLED)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from framegallery import main
from framegallery.repository.config_repository import ConfigKey


def test_batch_mode_never_pushes(monkeypatch) -> None:  # noqa: ANN001
    """In batch_slideshow mode the app must not push per-tick (the TV rotates)."""
    monkeypatch.setattr(main.settings, "upload_processor", "batch_slideshow")

    # Config is never consulted in batch mode.
    with patch.object(main, "SessionLocal") as session_local:
        assert main._should_push_slideshow_tick() is False  # noqa: SLF001
        session_local.assert_not_called()


def _repo(*, slideshow_enabled: bool = True, tv_watch_mode: bool = False) -> MagicMock:
    """Build a ConfigRepository stub that answers per key rather than uniformly."""
    values = {
        ConfigKey.SLIDESHOW_ENABLED: slideshow_enabled,
        ConfigKey.TV_WATCH_MODE_ENABLED: tv_watch_mode,
    }
    fake_repo = MagicMock()
    fake_repo.get_bool.side_effect = lambda key, **_: values[key]
    return fake_repo


def test_single_async_honours_enabled_flag(monkeypatch) -> None:  # noqa: ANN001
    """In single_async mode the tick follows the SLIDESHOW_ENABLED config flag."""
    monkeypatch.setattr(main.settings, "upload_processor", "single_async")
    fake_repo = _repo(slideshow_enabled=True)

    with (
        patch.object(main, "SessionLocal"),
        patch.object(main, "ConfigRepository", return_value=fake_repo),
    ):
        assert main._should_push_slideshow_tick() is True  # noqa: SLF001

    fake_repo.get_bool.assert_any_call(ConfigKey.SLIDESHOW_ENABLED, default=True)


def test_single_async_disabled_skips(monkeypatch) -> None:  # noqa: ANN001
    """When SLIDESHOW_ENABLED is false, the tick is skipped."""
    monkeypatch.setattr(main.settings, "upload_processor", "single_async")

    with (
        patch.object(main, "SessionLocal"),
        patch.object(main, "ConfigRepository", return_value=_repo(slideshow_enabled=False)),
    ):
        assert main._should_push_slideshow_tick() is False  # noqa: SLF001


def test_tv_watch_mode_skips_the_whole_tick(monkeypatch) -> None:  # noqa: ANN001
    """
    TV watch mode stops the tick outright, even with the slideshow enabled.

    Skipping the whole tick (rather than only the push) matters: advancing the
    slideshow would keep rewriting the active image and emitting SSE updates for
    pictures nobody is looking at, drifting the UI out of step with the screen.
    """
    monkeypatch.setattr(main.settings, "upload_processor", "single_async")

    with (
        patch.object(main, "SessionLocal"),
        patch.object(main, "ConfigRepository", return_value=_repo(slideshow_enabled=True, tv_watch_mode=True)),
    ):
        assert main._should_push_slideshow_tick() is False  # noqa: SLF001


def test_tv_watch_mode_is_checked_before_the_slideshow_flag(monkeypatch) -> None:  # noqa: ANN001
    """The watch-mode veto short-circuits, so SLIDESHOW_ENABLED is not even consulted."""
    monkeypatch.setattr(main.settings, "upload_processor", "single_async")
    fake_repo = _repo(slideshow_enabled=True, tv_watch_mode=True)

    with (
        patch.object(main, "SessionLocal"),
        patch.object(main, "ConfigRepository", return_value=fake_repo),
    ):
        main._should_push_slideshow_tick()  # noqa: SLF001

    fake_repo.get_bool.assert_called_once_with(ConfigKey.TV_WATCH_MODE_ENABLED, default=False)


@pytest.mark.asyncio
async def test_wait_for_processor_returns_true_when_connected() -> None:
    """The startup wait returns immediately once the processor is connected."""
    processor = MagicMock()
    processor.is_connected = True

    assert await main._wait_for_processor_connection(processor, timeout=5) is True  # noqa: SLF001


@pytest.mark.asyncio
async def test_wait_for_processor_times_out_when_never_connected() -> None:
    """The startup wait gives up after the timeout if the TV never connects."""
    processor = MagicMock()
    processor.is_connected = False

    with patch.object(main.asyncio, "sleep", new=AsyncMock()):
        result = await main._wait_for_processor_connection(processor, timeout=1.0, poll_interval=0.5)  # noqa: SLF001

    assert result is False
