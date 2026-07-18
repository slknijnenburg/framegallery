"""Factory for building the configured upload processor at startup."""

from __future__ import annotations

from typing import TYPE_CHECKING

from framegallery.frame_connector.processors.base import ProcessorKind, UploadProcessor

if TYPE_CHECKING:
    from framegallery.libraries.manager import LibraryManager


def build_processor(
    kind: ProcessorKind,
    ip_address: str,
    port: int,
    library_manager: LibraryManager | None = None,
) -> UploadProcessor:
    """
    Build the upload processor for the given kind.

    Imports are local so that unused strategies (and their dependencies) are never
    imported, and so importing this module stays cheap.
    """
    # Imports are local so that unused strategies (and their heavy TV-client deps)
    # are never imported for a given deployment.
    if kind == ProcessorKind.SINGLE_ASYNC:
        from framegallery.frame_connector.processors.single_async import SingleAsyncProcessor  # noqa: PLC0415

        return SingleAsyncProcessor(ip_address, port, library_manager)

    if kind == ProcessorKind.SYNC_THREAD:
        from framegallery.frame_connector.processors.sync_thread import SyncThreadProcessor  # noqa: PLC0415

        return SyncThreadProcessor(ip_address, port, library_manager)

    if kind == ProcessorKind.BATCH_SLIDESHOW:
        from framegallery.frame_connector.processors.batch_slideshow import BatchSlideshowProcessor  # noqa: PLC0415

        return BatchSlideshowProcessor(ip_address, port, library_manager)

    msg = f"Unknown upload processor kind: {kind!r}"
    raise ValueError(msg)
