"""
Centralized logging configuration for Race to the Crystal.

This module provides consistent logging setup across all components.
"""

import logging
import sys
from typing import Optional


# Default log format
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
SIMPLE_FORMAT = "%(levelname)s - %(name)s - %(message)s"


def setup_logger(
    name: str,
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    add_console_handler: bool = True
) -> logging.Logger:
    """
    Set up a logger with consistent formatting.

    Args:
        name: Logger name (usually __name__)
        level: Logging level (default: INFO)
        format_string: Custom format string (default: DEFAULT_FORMAT)
        add_console_handler: Whether to add console handler (default: True)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger

    if add_console_handler:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        formatter = logging.Formatter(format_string or DEFAULT_FORMAT)
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with default configuration.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def set_global_log_level(level: int) -> None:
    """
    Set log level for all existing loggers.

    Args:
        level: Logging level (e.g., logging.DEBUG, logging.INFO)
    """
    logging.root.setLevel(level)
    for logger in logging.Logger.manager.loggerDict.values():
        if isinstance(logger, logging.Logger):
            logger.setLevel(level)
