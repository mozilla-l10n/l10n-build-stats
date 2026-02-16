"""Centralized logging configuration for l10n-build-stats."""

from __future__ import annotations

import logging
import os
import sys

from pathlib import Path


# Default log format
DEFAULT_FORMAT = "%(levelname)s - %(message)s"
VERBOSE_FORMAT = (
    "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)


def setup_logging(
    level: int | str | None = None,
    format_string: str | None = None,
    log_file: str | None = None,
    verbose: bool = False,
) -> None:
    """
    Configure logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) or int.
               Defaults to INFO, or value from LOG_LEVEL env var.
        format_string: Custom log format string. Defaults to DEFAULT_FORMAT.
        log_file: Optional file path to write logs to.
        verbose: If True, uses VERBOSE_FORMAT with file/line info.

    Environment Variables:
        LOG_LEVEL: Set default logging level (e.g., "DEBUG", "INFO")
        LOG_FILE: Set default log file path
    """
    # Determine log level
    if level is None:
        level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_str, logging.INFO)
    elif isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    # Determine format
    if format_string is None:
        format_string = VERBOSE_FORMAT if verbose else DEFAULT_FORMAT

    # Get log file from env if not specified
    if log_file is None:
        log_file = os.environ.get("LOG_FILE")

    # Configure handlers
    handlers: list[logging.Handler] = []

    # Console handler (always present)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(format_string))
    handlers.append(console_handler)

    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(format_string))
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=handlers,
        force=True,  # Override any existing configuration
    )

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("gspread").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Starting process")
    """
    return logging.getLogger(name)
