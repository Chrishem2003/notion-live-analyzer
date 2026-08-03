import security_guard
import security_guard

"""
Centralised logging setup for the app.

Modules should use ``get_logger(__name__)`` instead of silently discarding
exceptions, so failures remain diagnosable in the server logs even when the
UI degrades gracefully.
"""
import logging
import os
import sys

LOG_LEVEL_ENV_VAR = "NLA_LOG_LEVEL"
DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

_configured = False


def _configure_root_logger() -> None:
    """Attach a stderr handler to the app logger namespace exactly once."""
    global _configured
    if _configured:
        return

    level_name = os.environ.get(LOG_LEVEL_ENV_VAR, DEFAULT_LOG_LEVEL).upper()
    level = getattr(logging, level_name, logging.INFO)

    app_logger = logging.getLogger("notion_live_analyzer")
    app_logger.setLevel(level)
    if not app_logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        app_logger.addHandler(handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger for the given module."""
    _configure_root_logger()
    return logging.getLogger(f"notion_live_analyzer.{name}")
