"""Logging setup with rotating files per module/service."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(
    name: str,
    log_dir: str | Path = "logs",
    level: str | int = "INFO",
    max_bytes: int = 10_000_000,
    backup_count: int = 5,
) -> logging.Logger:
    """Create an idempotent logger with console and rotating file handlers."""

    logger = logging.getLogger(name)
    numeric_level = logging.getLevelName(level) if isinstance(level, str) else level
    if isinstance(numeric_level, str):
        numeric_level = logging.INFO
    logger.setLevel(numeric_level)
    logger.propagate = False

    if logger.handlers:
        return logger

    Path(log_dir).mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(numeric_level)
    logger.addHandler(console)

    file_handler = RotatingFileHandler(
        Path(log_dir) / f"{name.replace('.', '_')}.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(numeric_level)
    logger.addHandler(file_handler)
    return logger
