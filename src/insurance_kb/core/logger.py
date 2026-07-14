"""Centralized logging configuration built on top of loguru.

This module configures a single, process-wide loguru logger with both a
console sink (human-readable, colorized) and a rotating file sink
(structured, for later inspection). All other modules should simply::

    from insurance_kb.core.logger import get_logger

    logger = get_logger(__name__)
    logger.info("message")

``get_logger`` returns the shared loguru logger bound with a ``module``
context field so log lines can be traced back to their origin even though
loguru does not use the standard library's per-module logger instances.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from loguru import logger as _loguru_logger

_CONFIGURED = False


def configure_logging(
    log_dir: str | Path = "logs",
    console_level: str = "INFO",
    file_level: str = "DEBUG",
    rotation: str = "10 MB",
    retention: str = "14 days",
    force: bool = False,
) -> None:
    """Configure the shared loguru logger with console and file sinks.

    This function is idempotent: calling it multiple times will not add
    duplicate sinks, unless ``force=True`` is passed. It should typically
    be called once, near process start-up (e.g. in ``scripts/run_pipeline.py``).

    Args:
        log_dir: Directory where rotating log files will be written.
        console_level: Minimum level printed to stdout.
        file_level: Minimum level written to the log file.
        rotation: loguru rotation policy (size- or time-based).
        retention: loguru retention policy for old log files.
        force: If ``True``, reconfigure even if already configured
            (primarily intended for tests).
    """
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    _loguru_logger.remove()  # remove default handler to avoid duplicate output

    _loguru_logger.add(
        sys.stdout,
        level=console_level,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[module]}</cyan> - <level>{message}</level>"
        ),
    )

    _loguru_logger.add(
        log_path / "pipeline_{time:YYYY-MM-DD}.log",
        level=file_level,
        rotation=rotation,
        retention=retention,
        encoding="utf-8",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{extra[module]} - {message}"
        ),
    )

    _CONFIGURED = True


def get_logger(module_name: str) -> Any:
    """Return the shared loguru logger bound with a module name.

    Args:
        module_name: Typically ``__name__`` of the calling module.

    Returns:
        A loguru logger instance bound with ``module`` in its extra context.
    """
    if not _CONFIGURED:
        configure_logging()
    return _loguru_logger.bind(module=module_name)
