"""Checkpoint creation and fallback policies."""
import os
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from src.config.settings import settings
from src.utils.logger import logger

try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    SqliteSaver = None

_sqlite_context_manager: Any = None


def resolve_checkpointer():
    """Return the configured LangGraph checkpointer."""
    global _sqlite_context_manager

    db_path = os.path.abspath(settings.database_path)
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    if SqliteSaver is None:
        logger.warning("SQLite checkpointer unavailable. Falling back to in-memory checkpoints.")
        return InMemorySaver()

    try:
        candidate = SqliteSaver.from_conn_string(db_path)

        if hasattr(candidate, "__enter__") and hasattr(candidate, "__exit__"):
            _sqlite_context_manager = candidate
            saver = _sqlite_context_manager.__enter__()
            logger.info("Using SQLite checkpointer at %s", db_path)
            return saver

        logger.info("Using SQLite checkpointer at %s", db_path)
        return candidate
    except Exception as exc:  # pragma: no cover - defensive path
        logger.warning("Failed to initialize SQLite checkpointer: %s", exc)
        return InMemorySaver()
