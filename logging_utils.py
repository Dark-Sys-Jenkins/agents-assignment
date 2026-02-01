import logging
from pathlib import Path
from typing import Optional


def configure_logger(
    name: str = "history-agent",
    log_file: Optional[Path] = None,
    level: int = logging.INFO,
) -> logging.Logger:
    logger = logging.getLogger(name)

    if not logger.handlers:
        if log_file is None:
            log_file = Path(__file__).parent / "history_agent.log"

        formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        logger.setLevel(level)
        logger.propagate = False

    # Ensure a file handler for the requested log file exists
    if log_file is None:
        log_file = Path(__file__).parent / "history_agent.log"

    if not any(
        isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) == str(log_file)
        for h in logger.handlers
    ):
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        )
        logger.addHandler(file_handler)

    return logger
