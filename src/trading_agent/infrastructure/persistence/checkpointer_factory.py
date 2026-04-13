"""Checkpointer creation and fallback policies."""
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
    """Return a valid checkpointer for workflow compilation."""
    global _sqlite_context_manager

    db_path = os.path.abspath(settings.database_path)
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)

    if SqliteSaver is None:
        logger.warning(
            "langgraph.checkpoint.sqlite is unavailable; using InMemorySaver "
            "(install langgraph-checkpoint-sqlite for persistent checkpoints)."
        )
        return InMemorySaver()

    try:
        sqlite_uri = f"sqlite:///{db_path.replace(os.sep, '/')}"
        candidate = SqliteSaver.from_conn_string(sqlite_uri)

        if hasattr(candidate, "__enter__") and hasattr(candidate, "__exit__"):
            _sqlite_context_manager = candidate
            saver = _sqlite_context_manager.__enter__()
            logger.info(f"Using SQLite checkpointer (context-managed) at {db_path}")
            return saver

        logger.info(f"Using SQLite checkpointer at {db_path}")
        return candidate
    except Exception as exc:
        logger.warning(
            f"SQLite checkpointer init failed ({exc}); falling back to InMemorySaver. "
            f"Check DATABASE_PATH: {db_path}"
        )
        return InMemorySaver()

