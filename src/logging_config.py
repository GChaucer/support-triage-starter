from __future__ import annotations

import logging

from src.config import LOGS_DIR


def configure_logging() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger()
    if logger.handlers:
        return

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(LOGS_DIR / "support_triage.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
