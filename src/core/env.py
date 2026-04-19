"""Minimal .env loading helpers for local development."""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(dotenv_path: Path) -> None:
    """Load simple KEY=VALUE pairs into the environment if unset."""
    if not dotenv_path.exists():
        return

    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        os.environ.setdefault(key, value)
