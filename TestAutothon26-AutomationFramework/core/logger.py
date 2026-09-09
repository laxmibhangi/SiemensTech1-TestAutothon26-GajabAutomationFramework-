"""Shared logging setup - one rotating log file per run plus console output."""
from __future__ import annotations

import logging
from datetime import datetime

from config.settings import LOG_DIR

_LOG_FILE = LOG_DIR / f"run_{datetime.now():%Y%m%d_%H%M%S}.log"
_configured = False


def get_logger(name: str) -> logging.Logger:
    global _configured
    if not _configured:
        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)-22s | %(message)s",
            datefmt="%H:%M:%S",
        )
        file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(fmt)

        root = logging.getLogger()
        root.setLevel(logging.INFO)
        root.addHandler(file_handler)
        _configured = True

    return logging.getLogger(name)
