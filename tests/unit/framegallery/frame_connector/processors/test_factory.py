"""Tests for the upload-processor factory."""

from unittest.mock import patch

import pytest

from framegallery.frame_connector.processors import ProcessorKind, build_processor
from framegallery.frame_connector.processors.batch_slideshow import BatchSlideshowProcessor
from framegallery.frame_connector.processors.single_async import SingleAsyncProcessor
from framegallery.frame_connector.processors.sync_thread import SyncThreadProcessor


def test_build_single_async_processor() -> None:
    """The factory builds a SingleAsyncProcessor for the single_async kind."""
    with patch("framegallery.frame_connector.processors.base.asyncio.create_task"):
        processor = build_processor(ProcessorKind.SINGLE_ASYNC, "192.168.1.100", 8002)

    assert isinstance(processor, SingleAsyncProcessor)
    assert processor.kind == ProcessorKind.SINGLE_ASYNC


def test_build_sync_thread_processor() -> None:
    """The factory builds a SyncThreadProcessor for the sync_thread kind."""
    with patch("framegallery.frame_connector.processors.base.asyncio.create_task"):
        processor = build_processor(ProcessorKind.SYNC_THREAD, "192.168.1.100", 8002)

    assert isinstance(processor, SyncThreadProcessor)
    assert processor.kind == ProcessorKind.SYNC_THREAD


def test_build_batch_slideshow_processor() -> None:
    """The factory builds a BatchSlideshowProcessor for the batch_slideshow kind."""
    with patch("framegallery.frame_connector.processors.base.asyncio.create_task"):
        processor = build_processor(ProcessorKind.BATCH_SLIDESHOW, "192.168.1.100", 8002)

    assert isinstance(processor, BatchSlideshowProcessor)
    assert processor.kind == ProcessorKind.BATCH_SLIDESHOW


def test_build_processor_passes_library_manager() -> None:
    """The factory forwards the library_manager to the processor."""
    sentinel = object()
    with patch("framegallery.frame_connector.processors.base.asyncio.create_task"):
        processor = build_processor(ProcessorKind.SINGLE_ASYNC, "192.168.1.100", 8002, sentinel)

    assert processor.library_manager is sentinel


def test_build_processor_unknown_kind_raises() -> None:
    """An unrecognised kind raises ValueError rather than returning None."""
    with pytest.raises(ValueError, match="Unknown upload processor"):
        build_processor("bogus", "192.168.1.100", 8002)  # type: ignore[arg-type]
