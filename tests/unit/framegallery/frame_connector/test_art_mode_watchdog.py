"""Unit tests for the art-mode watchdog."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from framegallery.frame_connector.art_mode_watchdog import ArtModeWatchdog, TvHealth


def _processor(*, powered: bool | None, art_mode: bool | None = None) -> MagicMock:
    """Build a processor stub whose two probes return the given readings."""
    processor = MagicMock()
    # Explicit: a bare MagicMock attribute is truthy by accident, and whether the
    # processor is connected now decides UNKNOWN vs ART_UNAVAILABLE.
    processor.is_connected = True
    processor.is_tv_powered_on = AsyncMock(return_value=powered)
    processor.get_art_mode = AsyncMock(return_value=art_mode)
    processor.set_art_mode = AsyncMock(return_value=True)
    processor.close = AsyncMock()
    processor.note_art_mode = MagicMock()
    return processor


def _watchdog(processor: MagicMock) -> ArtModeWatchdog:
    return ArtModeWatchdog(processor, poll_interval=60)


@pytest.mark.asyncio
async def test_art_on_when_powered_and_art_mode_active() -> None:
    """The healthy case: REST says powered, the art channel says art mode is on."""
    processor = _processor(powered=True, art_mode=True)

    assert await _watchdog(processor).probe_once() is TvHealth.ART_ON
    processor.note_art_mode.assert_called_once_with(active=True)


@pytest.mark.asyncio
async def test_tv_mode_when_art_mode_off() -> None:
    """Powered with art mode off is TV_MODE, and gates the slideshow."""
    processor = _processor(powered=True, art_mode=False)

    assert await _watchdog(processor).probe_once() is TvHealth.TV_MODE
    processor.note_art_mode.assert_called_once_with(active=False)


@pytest.mark.asyncio
async def test_standby_when_not_powered() -> None:
    """A reachable but powered-down TV is STANDBY, and the art channel is not probed."""
    processor = _processor(powered=False)

    assert await _watchdog(processor).probe_once() is TvHealth.STANDBY
    processor.get_art_mode.assert_not_awaited()
    # Standby is not an art-mode reading, so it must not gate the slideshow.
    processor.note_art_mode.assert_called_once_with(active=None)


@pytest.mark.asyncio
async def test_unreachable_when_rest_probe_fails() -> None:
    """No REST answer at all means the whole TV is gone, not that art mode is off."""
    processor = _processor(powered=None)

    assert await _watchdog(processor).probe_once() is TvHealth.UNREACHABLE
    processor.note_art_mode.assert_called_once_with(active=None)


@pytest.mark.asyncio
async def test_art_unavailable_when_rest_answers_but_art_channel_does_not() -> None:
    """
    REST up + art channel silent is the art-crash signature.

    This is the distinction that ICMP alone cannot make, and the reason the watchdog
    probes power state over REST separately from the art WebSocket.
    """
    processor = _processor(powered=True, art_mode=None)

    assert await _watchdog(processor).probe_once() is TvHealth.ART_UNAVAILABLE
    # "Could not ask" must not be recorded as a confident "off".
    processor.note_art_mode.assert_called_once_with(active=None)


@pytest.mark.asyncio
async def test_watchdog_never_forces_art_mode_on() -> None:
    """
    The periodic probe must never restore art mode.

    Between our own writes an "off" is indistinguishable from someone choosing to
    watch television, so forcing it back on would fight the person holding the remote.
    Restoring is done only by the post-write check, where causation is established.
    """
    processor = _processor(powered=True, art_mode=False)

    await _watchdog(processor).probe_once()

    processor.set_art_mode.assert_not_awaited()


@pytest.mark.asyncio
async def test_connection_is_dropped_on_entering_a_bad_state() -> None:
    """A wedged art channel does not heal itself, so the connection is torn down."""
    processor = _processor(powered=True, art_mode=None)

    await _watchdog(processor).probe_once()

    processor.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_connection_is_not_dropped_repeatedly_while_bad() -> None:
    """
    Recovery fires on the transition, not on every poll.

    The reconnection pinger is already running while disconnected; closing on each
    poll would fight it and spam the log for as long as the TV stays unreachable.
    """
    processor = _processor(powered=None)
    watchdog = _watchdog(processor)

    for _ in range(3):
        await watchdog.probe_once()

    processor.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_recovery_rearms_after_returning_to_health() -> None:
    """Going bad, healthy, then bad again drops the connection on each fresh failure."""
    processor = _processor(powered=None)
    watchdog = _watchdog(processor)

    await watchdog.probe_once()

    processor.is_tv_powered_on.return_value = True
    processor.get_art_mode.return_value = True
    await watchdog.probe_once()
    assert watchdog.health is TvHealth.ART_ON

    processor.is_tv_powered_on.return_value = None
    await watchdog.probe_once()

    expected_drops = 2  # one per fresh entry into a bad state
    assert processor.close.await_count == expected_drops


@pytest.mark.asyncio
async def test_probe_failure_does_not_kill_the_state() -> None:
    """A probe that raises propagates from probe_once (the loop is what swallows it)."""
    processor = _processor(powered=True)
    processor.is_tv_powered_on = AsyncMock(side_effect=OSError("boom"))

    with pytest.raises(OSError, match="boom"):
        await _watchdog(processor).probe_once()


@pytest.mark.asyncio
async def test_not_yet_connected_is_unknown_not_a_crash_report() -> None:
    """
    Before the TV connection is up, the state is unknown -- not a crashed art system.

    get_art_mode() returns None both when the art channel is wedged and when the
    processor simply has no connection yet. Conflating them made every startup log
    "the art system has most likely crashed", which is not merely noise: it was read
    as evidence of a real fault during an incident and sent the diagnosis the wrong
    way.
    """
    processor = _processor(powered=True, art_mode=None)
    processor.is_connected = False

    assert await _watchdog(processor).probe_once() is TvHealth.UNKNOWN
    processor.note_art_mode.assert_called_once_with(active=None)


@pytest.mark.asyncio
async def test_connected_but_silent_art_channel_is_still_a_crash_report() -> None:
    """With a live connection, an unanswerable art channel does mean the art system wedged."""
    processor = _processor(powered=True, art_mode=None)
    processor.is_connected = True

    assert await _watchdog(processor).probe_once() is TvHealth.ART_UNAVAILABLE
