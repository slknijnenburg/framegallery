import logging
import sys
from pathlib import Path


def setup_logging(
    log_level: str = "INFO",
    websocket_log_level: str = "WARNING",
    logs_path: str = "./logs",
) -> logging.Logger:
    """
    Set up logging for the application, including file and stream handlers.

    ``logs_path`` is the directory the ``framegallery.log`` file is written to.

    ``websocket_log_level`` is applied to the WebSocket libraries used for the
    Samsung Frame connection (``websockets`` and ``samsungtvws``). These emit very
    verbose ping/pong/keepalive messages at DEBUG level, so they are pinned to a
    separate level (default ``WARNING``) independently of the app-wide ``log_level``.
    Raise it to ``DEBUG`` only when you need to debug the TV connection itself.
    """
    log_dir = Path(logs_path)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "framegallery.log"

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # File Handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Stream Handler (stdout)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Add handlers if they aren't already present for their type
    handler_types = {type(h) for h in root_logger.handlers}
    if logging.FileHandler not in handler_types:
        root_logger.addHandler(file_handler)
    if logging.StreamHandler not in handler_types:
        root_logger.addHandler(stream_handler)

    # Custom app logger (optional, for direct use)
    logger = logging.getLogger("framegallery")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.propagate = True  # Let messages bubble up to root

    # Pin the WebSocket libraries to their own level so their verbose
    # ping/pong/keepalive DEBUG messages don't flood the logs when the app runs
    # at DEBUG. They still propagate to the handlers above, but are filtered here.
    ws_level = getattr(logging, websocket_log_level.upper(), logging.WARNING)
    for ws_logger_name in ("websockets", "samsungtvws"):
        logging.getLogger(ws_logger_name).setLevel(ws_level)

    return logger
