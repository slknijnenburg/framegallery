import logging
import os
import sys

def setup_logging(log_level="INFO"):
    log_dir = "./logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "framegallery.log")

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

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

    return logger
