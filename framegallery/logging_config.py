import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def setup_logging(
    log_level: str = "INFO",
    websocket_log_level: str = "WARNING",
    logs_path: str = "./logs",
) -> logging.Logger:
    """
    Set up logging for the application, including file and stream handlers.

    ``logs_path`` is the directory the ``framegallery.log`` file is written to.

    The file is rotated at midnight UTC and the last 7 days are kept, so it cannot
    grow without bound. The stdout stream is captured by Docker instead, and is
    capped by the ``logging`` options in ``docker-compose.yml``.

    ``websocket_log_level`` is applied to the WebSocket libraries used for the
    Samsung Frame connection (``websockets`` and ``samsungtvws``). These emit very
    verbose ping/pong/keepalive messages at DEBUG level, so they are pinned to a
    separate level (default ``WARNING``) independently of the app-wide ``log_level``.
    Raise it to ``DEBUG`` only when you need to debug the TV connection itself.
    """
    log_dir = Path(logs_path)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "framegallery.log"

    level = getattr(logging, log_level.upper(), logging.INFO)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # setup_logging() is called from several modules, so only attach a handler when
    # ours is missing -- and build it lazily, because constructing a file handler
    # already opens the file. Two rotating handlers on one file would each write every
    # record *and* both try to roll it over at midnight, fighting over the inode.
    #
    # Both checks match on the handler's target rather than just its class, so a
    # foreign handler on the root logger neither satisfies nor blocks our own. Note
    # logging.FileHandler subclasses StreamHandler, hence the explicit exclusion in
    # the console check.
    #
    # The console check accepts a handler on *either* standard stream: something else
    # attaching one (logging.basicConfig() adds a stderr handler, for instance) means
    # the console is already served, and adding ours would emit every record twice --
    # doubling the very Docker log this rotation is meant to bound. A handler writing
    # somewhere other than a console (pytest's caplog, an in-memory buffer) is not a
    # substitute, so it must not suppress ours.
    console_streams = (sys.stdout, sys.stderr)
    log_file_path = os.path.abspath(log_file)  # noqa: PTH100 -- must match FileHandler.baseFilename
    has_file_handler = any(
        isinstance(h, logging.FileHandler) and h.baseFilename == log_file_path for h in root_logger.handlers
    )
    has_stream_handler = any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) and h.stream in console_streams
        for h in root_logger.handlers
    )

    # File handler: roll over at midnight UTC, keeping a week of history.
    if not has_file_handler:
        file_handler = TimedRotatingFileHandler(
            log_file,
            when="midnight",
            backupCount=7,
            utc=True,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        root_logger.addHandler(file_handler)

    # Console handler (stdout): captured by Docker, capped in docker-compose.yml.
    if not has_stream_handler:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(level)
        root_logger.addHandler(stream_handler)

    # Custom app logger (optional, for direct use)
    logger = logging.getLogger("framegallery")
    logger.setLevel(level)
    logger.propagate = True  # Let messages bubble up to root

    # Pin the WebSocket libraries to their own level so their verbose
    # ping/pong/keepalive DEBUG messages don't flood the logs when the app runs
    # at DEBUG. They still propagate to the handlers above, but are filtered here.
    ws_level = getattr(logging, websocket_log_level.upper(), logging.WARNING)
    for ws_logger_name in ("websockets", "samsungtvws"):
        logging.getLogger(ws_logger_name).setLevel(ws_level)

    return logger
