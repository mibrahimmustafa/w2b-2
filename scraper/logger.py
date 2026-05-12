"""
scraper.logger
==============
Centralised logging factory.

Every module obtains a child logger via ``get_logger(__name__)``.
The root logger is configured once — subsequent calls are no-ops
(handlers are never duplicated).

Log levels:
    • Console  → INFO  (coloured prefix where terminal supports it)
    • File     → DEBUG (rotating, keeps last 3 runs × 5 MB)
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_LOG_DIR = Path(f"logs_{datetime.now().strftime('%Y-%m-%d')}")
_LOG_FILE = _LOG_DIR / "w2b_scraper.log"
_MAX_BYTES = 5 * 1024 * 1024   # 5 MB per file
_BACKUP_COUNT = 3
_FMT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
_DATE_FMT = "%H:%M:%S"

_ROOT_LOGGER_NAME = "W2B"
_configured = False  # module-level guard


def _configure_root() -> None:
    """Set up handlers on the root W2B logger exactly once."""
    global _configured
    if _configured:
        return

    root = logging.getLogger(_ROOT_LOGGER_NAME)
    root.setLevel(logging.DEBUG)  # root captures everything; handlers filter

    formatter = logging.Formatter(_FMT, datefmt=_DATE_FMT)

    # ── Console handler (INFO+) ──────────────────────────────────────────────
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    root.addHandler(console)

    # ── Rotating file handler (DEBUG+) ───────────────────────────────────────
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            _LOG_FILE,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError:
        # Non-fatal — continue with console-only logging
        root.warning("Could not create log file at %s; logging to console only.", _LOG_FILE)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Return a child logger under the W2B namespace.

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A configured :class:`logging.Logger` instance.

    Example::

        from scraper.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Ready.")
    """
    _configure_root()
    # Nest the logger under the root so it inherits handlers
    qualified = f"{_ROOT_LOGGER_NAME}.{name}" if not name.startswith(_ROOT_LOGGER_NAME) else name
    return logging.getLogger(qualified)
