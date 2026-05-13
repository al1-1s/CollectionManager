"""Application logging helpers built on top of loguru.

This module does not perform initialization on import. Call
`init_logging()` from `bootstrap` during application startup.
"""

from __future__ import annotations

import logging as std_logging
import sys
from pathlib import Path

from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LOG_DIR = PROJECT_ROOT / "logs"
DEFAULT_LOG_FILE = "collection_manager_{time:YYYY-MM-DD}.log"
DEFAULT_LEVEL = "INFO"
LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level:<8} | "
    "{process.id}:{thread.name} | "
    "{name}:{function}:{line} - {message}"
)


class InterceptHandler(std_logging.Handler):
    """Forward standard logging records to loguru."""

    def emit(self, record: std_logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame = std_logging.currentframe()
        depth = 2
        while frame is not None and frame.f_code.co_filename == std_logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def _is_compiled() -> bool:
    """Return whether this module is running from a Nuitka build."""

    return "__compiled__" in globals()


def get_default_log_dir() -> Path:
    """Return the default log directory for source runs and packaged builds."""

    if _is_compiled():
        return Path(sys.argv[0]).resolve().parent / "logs"

    return DEFAULT_LOG_DIR


def get_logger():
    """Return the shared loguru logger instance."""

    return logger


def init_logging(
    level: str = DEFAULT_LEVEL,
    log_dir: Path | None = None,
    log_file: str = DEFAULT_LOG_FILE,
) -> None:
    """Configure console and file sinks for the application."""

    output_dir = log_dir or get_default_log_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.remove()
    std_logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    std_logging.captureWarnings(True)

    logger.add(
        sys.stderr,
        level=level,
        format=LOG_FORMAT,
        colorize=True,
        enqueue=True,
        backtrace=True,
        diagnose=False,
    )
    logger.add(
        output_dir / log_file,
        level=level,
        format=LOG_FORMAT,
        rotation="00:00",
        retention="5 days",
        compression=None,
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=False,
    )

    logger.info(f"Logging initialized with level {level}. Logs directory: {output_dir}")
