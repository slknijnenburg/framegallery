"""Tests for the /api/status endpoint's view of TV health."""

from types import SimpleNamespace

import pytest

from framegallery import main
from framegallery.frame_connector.art_mode_watchdog import TvHealth


def _install_state(monkeypatch, health: TvHealth | None, *, art_mode: bool | None) -> None:  # noqa: ANN001
    """Point app.state at a stub watchdog/processor pair."""
    watchdog = None if health is None else SimpleNamespace(health=health)
    monkeypatch.setattr(main.app.state, "art_mode_watchdog", watchdog, raising=False)
    monkeypatch.setattr(
        main.app.state,
        "upload_processor",
        SimpleNamespace(art_mode_active=art_mode),
        raising=False,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("health", "expected_tv_on"),
    [
        (TvHealth.ART_ON, True),
        (TvHealth.TV_MODE, True),
        (TvHealth.ART_UNAVAILABLE, True),
        (TvHealth.STANDBY, False),
        (TvHealth.UNREACHABLE, False),
        (TvHealth.UNKNOWN, False),
    ],
)
async def test_tv_on_reflects_health(monkeypatch, health: TvHealth, expected_tv_on: bool) -> None:  # noqa: ANN001, FBT001
    """tv_on means "the TV is answering", which TV_MODE and a wedged art channel still are."""
    _install_state(monkeypatch, health, art_mode=None)

    assert (await main.status()).tv_on is expected_tv_on


@pytest.mark.asyncio
async def test_art_mode_is_reported_from_the_processor_cache(monkeypatch) -> None:  # noqa: ANN001
    """The endpoint serves the cached reading rather than probing the TV per request."""
    _install_state(monkeypatch, TvHealth.TV_MODE, art_mode=False)

    assert (await main.status()).art_mode_active is False


@pytest.mark.asyncio
async def test_art_mode_unknown_when_watchdog_is_disabled(monkeypatch) -> None:  # noqa: ANN001
    """
    With no watchdog nothing observes the TV.

    Reporting art_mode_active=True here (as the old stub did) would be inventing a
    value the app has no way of knowing.
    """
    _install_state(monkeypatch, None, art_mode=None)

    result = await main.status()

    assert result.art_mode_active is None
    assert result.tv_on is False
