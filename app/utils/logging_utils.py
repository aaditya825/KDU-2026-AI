"""
app/utils/logging_utils.py
──────────────────────────
Structured logger factory for the Content Accessibility Suite.

Usage
-----
    from app.utils.logging_utils import get_logger
    log = get_logger(__name__)
    log.info("Processing started", extra={"file_id": "abc123"})
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any


class _JsonFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Merge any extra fields passed via `extra=`
        for key, value in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "id", "levelname", "levelno",
                "lineno", "message", "module", "msecs", "msg", "name",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "taskName", "thread", "threadName",
            ):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def get_logger(name: str, json_output: bool = False) -> logging.Logger:
    """
    Return a named logger.

    Parameters
    ----------
    name:
        Typically ``__name__`` of the calling module.
    json_output:
        When True, attach a JSON formatter (useful for log aggregation).
        Defaults to False (uses the root handler set up by settings.configure_logging).
    """
    logger = logging.getLogger(name)
    if json_output and not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_JsonFormatter(datefmt="%Y-%m-%dT%H:%M:%SZ"))
        logger.addHandler(handler)
        logger.propagate = False
    return logger
