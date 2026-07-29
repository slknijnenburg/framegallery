"""
Periodic health probe for the TV's art mode.

The Frame drops out of art mode for two very different reasons: somebody picks up the
remote to watch television, or the art system crashes and the TV falls back to regular
TV (typically Samsung TV Plus). From the outside these look identical -- ``get_artmode``
simply reports ``off`` in both cases -- so this watchdog never tries to guess between
them. It observes, gates the slideshow, and recovers the *connection*; the one place
art mode is forced back on is immediately after our own writes, where causation is
established by construction (see ``UploadProcessor.verify_art_mode_after_write``).

What it does resolve is the far more important distinction between "the TV is fine but
art mode is off" and "the TV is not answering at all", by probing REST power state
separately from the art WebSocket. That is what lets a wedged art channel be detected
and reconnected instead of silently retrying into a dead socket every slideshow tick.
"""

from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from framegallery.frame_connector.processors import UploadProcessor

logger = logging.getLogger("framegallery")


class TvHealth(str, Enum):
    """Coarse health of the TV as seen from the app."""

    UNKNOWN = "unknown"
    """Nothing has been probed yet."""

    ART_ON = "art_on"
    """Reachable and displaying art. The normal state."""

    TV_MODE = "tv_mode"
    """Reachable, art mode off. Someone is watching television, or art mode crashed."""

    STANDBY = "standby"
    """Reachable but powered down (screen off). Normal overnight."""

    ART_UNAVAILABLE = "art_unavailable"
    """REST answers but the art channel does not -- the art system has wedged."""

    UNREACHABLE = "unreachable"
    """No response at all: powered off at the socket, rebooting, or off the network."""


# States in which the TV connection is worth tearing down so the reconnection pinger
# rebuilds it. A wedged art channel does not heal on its own.
_RECOVERABLE = frozenset({TvHealth.ART_UNAVAILABLE, TvHealth.UNREACHABLE})


def _art_mode_for(health: TvHealth) -> bool | None:
    """
    Map a health state onto a cached art-mode value.

    Only ART_ON and TV_MODE are confident readings. Every other state means we could
    not actually observe art mode, and must report None rather than a misleading
    False -- a False would gate the slideshow off (see ``art_mode_permits_upload``).
    """
    if health is TvHealth.ART_ON:
        return True
    if health is TvHealth.TV_MODE:
        return False
    return None


class ArtModeWatchdog:
    """Polls TV/art-mode health and keeps the processor's cached state fresh."""

    def __init__(self, processor: UploadProcessor, poll_interval: float) -> None:
        self._processor = processor
        self._poll_interval = poll_interval
        self._health = TvHealth.UNKNOWN

    @property
    def health(self) -> TvHealth:
        """The most recently observed health state."""
        return self._health

    async def run_periodic_probe(self) -> None:
        """Probe forever. A failing probe must never kill the loop."""
        logger.info("Art-mode watchdog started (every %ss)", self._poll_interval)
        while True:
            try:
                await self.probe_once()
            except Exception:
                logger.exception("Art-mode watchdog probe failed; will retry next cycle")
            await asyncio.sleep(self._poll_interval)

    async def probe_once(self) -> TvHealth:
        """Run a single probe, update cached state, and recover the connection if needed."""
        health = await self._classify()
        previous, self._health = self._health, health

        if health != previous:
            self._log_transition(previous, health)

        # Only art mode being *confidently* off should gate uploads. Everything else is
        # either fine or a connection problem, which the processor's own guards handle.
        self._processor.note_art_mode(active=_art_mode_for(health))

        # Re-arm the connection only on entering a bad state, not on every poll: the
        # reconnection pinger is already running while disconnected, and closing
        # repeatedly would fight it (and spam the log overnight).
        if health in _RECOVERABLE and previous not in _RECOVERABLE:
            await self._recover_connection(health)

        return health

    async def _classify(self) -> TvHealth:
        """Probe REST first, then the art channel, and map the pair onto a health state."""
        powered = await self._processor.is_tv_powered_on()
        if powered is None:
            return TvHealth.UNREACHABLE
        if not powered:
            return TvHealth.STANDBY

        art_mode = await self._processor.get_art_mode()
        if art_mode is None:
            # REST answered but the art channel did not: the TV is alive and the art
            # system specifically has wedged. This is the signature of an Art Mode
            # crash, as opposed to the TV being off or someone watching television.
            return TvHealth.ART_UNAVAILABLE
        return TvHealth.ART_ON if art_mode else TvHealth.TV_MODE

    async def _recover_connection(self, health: TvHealth) -> None:
        """Drop the TV connection so the reconnection pinger rebuilds it."""
        logger.warning("TV health is %s; dropping the connection so it gets rebuilt", health.value)
        try:
            await self._processor.close()
        except Exception:
            logger.exception("Failed to close the TV connection during art-mode recovery")

    def _log_transition(self, previous: TvHealth, current: TvHealth) -> None:
        """Log a health change, loudly enough to correlate with a Frame falling over."""
        if current is TvHealth.TV_MODE:
            logger.warning(
                "TV is no longer in art mode (%s -> %s). Treating this as someone watching "
                "television and pausing slideshow pushes; it will resume automatically when "
                "art mode returns. Note an art-mode crash between writes is indistinguishable "
                "from this and would look the same.",
                previous.value,
                current.value,
            )
        elif current is TvHealth.ART_UNAVAILABLE:
            logger.error(
                "TV answers over REST but its art channel does not (%s -> %s): the art system has most likely crashed.",
                previous.value,
                current.value,
            )
        else:
            logger.info("TV health: %s -> %s", previous.value, current.value)
