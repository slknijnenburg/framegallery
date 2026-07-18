"""
Pluggable upload processors for pushing images to the Samsung Frame TV.

Each processor implements a different strategy for getting images onto the TV,
selected at startup via ``settings.upload_processor``. This lets us A/B test the
upload mechanism to isolate what causes the TV to crash in Art Mode:

- ``single_async``   : the original behaviour (async WebSocket, one image at a
  time: upload -> activate -> delete previous).
- ``sync_thread``    : one image at a time, but via the synchronous ``samsungtvws``
  client run in a thread, with idle-recycle, Wake-on-LAN and bounded retries.
- ``batch_slideshow``: upload a batch of images once and let the TV's own
  slideshow rotate them.
"""

from framegallery.frame_connector.processors.base import (
    ProcessorKind,
    TvConnectionTimeoutError,
    TvNotConnectedError,
    UploadProcessor,
    api_version,
)
from framegallery.frame_connector.processors.factory import build_processor

__all__ = [
    "ProcessorKind",
    "TvConnectionTimeoutError",
    "TvNotConnectedError",
    "UploadProcessor",
    "api_version",
    "build_processor",
]
