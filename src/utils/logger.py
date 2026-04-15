"""Logging bootstrap utilities."""

from __future__ import annotations

import logging
import logging.config
from pathlib import Path
from typing import Any


def configure_logging(config_path: str | Path = "config/logging.yaml") -> None:
    target = Path(config_path)
    if not target.exists():
        logging.basicConfig(level=logging.INFO)
        return

    try:
        import yaml
    except ImportError:
        logging.basicConfig(level=logging.INFO)
        return

    config: dict[str, Any] = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if config:
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=logging.INFO)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
