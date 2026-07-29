"""Tests for the log-file rotation and handler de-duplication in setup_logging()."""

import io
import logging
import sys
from collections.abc import Iterator
from logging.handlers import TimedRotatingFileHandler

import pytest

from framegallery.logging_config import setup_logging

# Days of history the rotating file handler is expected to keep.
EXPECTED_BACKUP_COUNT = 7


@pytest.fixture
def clean_root_logger() -> Iterator[logging.Logger]:
    """Give each test a pristine root logger and restore it afterwards."""
    root_logger = logging.getLogger()
    saved_handlers = root_logger.handlers[:]
    saved_level = root_logger.level
    root_logger.handlers = []
    yield root_logger
    for handler in root_logger.handlers:
        handler.close()
    root_logger.handlers = saved_handlers
    root_logger.setLevel(saved_level)


def _file_handlers(root_logger: logging.Logger) -> list[logging.Handler]:
    return [h for h in root_logger.handlers if isinstance(h, logging.FileHandler)]


def _stream_handlers(root_logger: logging.Logger) -> list[logging.Handler]:
    """Return our stdout handlers only -- pytest injects its own StreamHandler into root."""
    return [
        h
        for h in root_logger.handlers
        if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) and h.stream is sys.stdout
    ]


def _console_handlers(root_logger: logging.Logger) -> list[logging.Handler]:
    """Return handlers writing to either standard stream, whoever attached them."""
    return [
        h
        for h in root_logger.handlers
        if isinstance(h, logging.StreamHandler)
        and not isinstance(h, logging.FileHandler)
        and h.stream in (sys.stdout, sys.stderr)
    ]


def test_file_handler_rotates_with_seven_day_retention(clean_root_logger: logging.Logger, tmp_path) -> None:  # noqa: ANN001
    """The log file must roll over at midnight UTC and keep a week of history."""
    setup_logging(log_level="DEBUG", logs_path=str(tmp_path))

    handlers = _file_handlers(clean_root_logger)
    assert len(handlers) == 1

    handler = handlers[0]
    assert isinstance(handler, TimedRotatingFileHandler)
    assert handler.when == "MIDNIGHT"
    assert handler.backupCount == EXPECTED_BACKUP_COUNT
    assert handler.utc is True


def test_rollover_preserves_previous_day(clean_root_logger: logging.Logger, tmp_path) -> None:  # noqa: ANN001
    """A rollover moves existing records aside and starts a fresh current log."""
    logger = setup_logging(log_level="DEBUG", logs_path=str(tmp_path))
    logger.info("before rollover")

    handler = _file_handlers(clean_root_logger)[0]
    assert isinstance(handler, TimedRotatingFileHandler)
    handler.doRollover()
    logger.info("after rollover")
    handler.flush()

    current = tmp_path / "framegallery.log"
    rolled = [p for p in tmp_path.iterdir() if p.name != "framegallery.log"]

    assert len(rolled) == 1
    assert "after rollover" in current.read_text()
    assert "before rollover" not in current.read_text()
    assert "before rollover" in rolled[0].read_text()


def test_both_handler_kinds_are_attached(clean_root_logger: logging.Logger, tmp_path) -> None:  # noqa: ANN001
    """
    Install a rotating file handler and a stdout stream handler.

    logging.FileHandler subclasses StreamHandler, so a naive isinstance check would
    treat the file handler as satisfying the stdout requirement and never attach one.
    """
    setup_logging(log_level="DEBUG", logs_path=str(tmp_path))

    assert len(_file_handlers(clean_root_logger)) == 1
    assert len(_stream_handlers(clean_root_logger)) == 1


def test_repeated_calls_do_not_duplicate_handlers(clean_root_logger: logging.Logger, tmp_path) -> None:  # noqa: ANN001
    """
    Avoid accumulating handlers -- setup_logging() is called from several modules.

    Duplicates would write every record more than once and, worse, have multiple
    rotating handlers fight over rolling the same file at midnight.
    """
    for _ in range(3):
        setup_logging(log_level="DEBUG", logs_path=str(tmp_path))

    assert len(_file_handlers(clean_root_logger)) == 1
    assert len(_stream_handlers(clean_root_logger)) == 1


def test_existing_console_handler_is_not_duplicated(clean_root_logger: logging.Logger, tmp_path) -> None:  # noqa: ANN001
    """
    A console handler on the other standard stream already serves the console.

    logging.basicConfig() attaches a stderr handler, for instance. Adding ours on top
    would emit every record twice and double the Docker log this rotation bounds.
    """
    clean_root_logger.addHandler(logging.StreamHandler(sys.stderr))

    setup_logging(log_level="DEBUG", logs_path=str(tmp_path))

    assert len(_file_handlers(clean_root_logger)) == 1
    assert len(_console_handlers(clean_root_logger)) == 1
    assert len(_stream_handlers(clean_root_logger)) == 0


def test_non_console_handler_does_not_block_ours(clean_root_logger: logging.Logger, tmp_path) -> None:  # noqa: ANN001
    """A handler writing somewhere other than a console is no substitute for stdout."""
    clean_root_logger.addHandler(logging.StreamHandler(io.StringIO()))

    setup_logging(log_level="DEBUG", logs_path=str(tmp_path))

    assert len(_file_handlers(clean_root_logger)) == 1
    assert len(_stream_handlers(clean_root_logger)) == 1


def test_only_one_log_file_is_opened(clean_root_logger: logging.Logger, tmp_path) -> None:  # noqa: ANN001, ARG001
    """Handlers are built lazily, so repeat calls must not open extra file objects."""
    for _ in range(3):
        setup_logging(log_level="DEBUG", logs_path=str(tmp_path))

    logging.getLogger("framegallery").info("hello")

    assert (tmp_path / "framegallery.log").read_text().count("hello") == 1


def test_level_is_applied_to_handlers(clean_root_logger: logging.Logger, tmp_path) -> None:  # noqa: ANN001
    """The configured level reaches the root logger and both handlers."""
    setup_logging(log_level="WARNING", logs_path=str(tmp_path))

    assert clean_root_logger.level == logging.WARNING
    assert _file_handlers(clean_root_logger)[0].level == logging.WARNING
    assert _stream_handlers(clean_root_logger)[0].level == logging.WARNING
