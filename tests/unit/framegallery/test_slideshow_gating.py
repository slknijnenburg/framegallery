"""Tests for the periodic slideshow-tick gating (GAP 1: SLIDESHOW_ENABLED)."""

from unittest.mock import MagicMock, patch

from framegallery import main
from framegallery.repository.config_repository import ConfigKey


def test_batch_mode_never_pushes(monkeypatch) -> None:  # noqa: ANN001
    """In batch_slideshow mode the app must not push per-tick (the TV rotates)."""
    monkeypatch.setattr(main.settings, "upload_processor", "batch_slideshow")

    # Config is never consulted in batch mode.
    with patch.object(main, "SessionLocal") as session_local:
        assert main._should_push_slideshow_tick() is False  # noqa: SLF001
        session_local.assert_not_called()


def test_single_async_honours_enabled_flag(monkeypatch) -> None:  # noqa: ANN001
    """In single_async mode the tick follows the SLIDESHOW_ENABLED config flag."""
    monkeypatch.setattr(main.settings, "upload_processor", "single_async")

    fake_repo = MagicMock()
    fake_repo.get_bool.return_value = True

    with (
        patch.object(main, "SessionLocal"),
        patch.object(main, "ConfigRepository", return_value=fake_repo),
    ):
        assert main._should_push_slideshow_tick() is True  # noqa: SLF001
        fake_repo.get_bool.assert_called_once_with(ConfigKey.SLIDESHOW_ENABLED, default=True)


def test_single_async_disabled_skips(monkeypatch) -> None:  # noqa: ANN001
    """When SLIDESHOW_ENABLED is false, the tick is skipped."""
    monkeypatch.setattr(main.settings, "upload_processor", "single_async")

    fake_repo = MagicMock()
    fake_repo.get_bool.return_value = False

    with (
        patch.object(main, "SessionLocal"),
        patch.object(main, "ConfigRepository", return_value=fake_repo),
    ):
        assert main._should_push_slideshow_tick() is False  # noqa: SLF001
