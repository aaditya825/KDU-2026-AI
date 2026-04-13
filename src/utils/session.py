"""Streamlit session management utilities"""
from datetime import datetime
import uuid

import streamlit as st

from src.utils.logger import logger

DEFAULT_SEED_PORTFOLIO = {
    "AAPL": 10,
    "GOOGL": 5,
}


def _session_defaults() -> dict:
    """Return mutable session defaults for new or reset sessions."""
    return {
        "portfolio": DEFAULT_SEED_PORTFOLIO.copy(),
        "stock_prices": {},
        "total_value": None,
        "currency": "USD",
        "messages": [],
        "pending_trade": None,
        "approval_required": False,
        "approval_granted": None,
        "value_history": [],
        "observability": {},
        "market_data_initialized": False,
        "market_data_attempted": False,
        "market_data_error": None,
    }


def _apply_defaults(defaults: dict) -> None:
    """Apply values into Streamlit session state."""
    for key, value in defaults.items():
        st.session_state[key] = value


def init_session_state():
    """Initialize Streamlit session state with defaults"""

    if "initialized" not in st.session_state:
        logger.info("Initializing Streamlit session state")

        # Generate unique thread ID per user session
        st.session_state.thread_id = f"user-{uuid.uuid4().hex[:8]}"
        logger.debug(f"Generated thread_id: {st.session_state.thread_id}")

        # Session data
        _apply_defaults(_session_defaults())
        st.session_state.initialized = True

        logger.info(f"Session initialized with seed portfolio: {st.session_state.portfolio}")


def get_thread_config() -> dict:
    """
    Returns LangGraph config with current thread_id.

    Returns:
        dict: Config for LangGraph invocation
    """
    return {"configurable": {"thread_id": st.session_state.thread_id}}


def add_message_to_history(role: str, content: str):
    """
    Add a message to session history for persistence.

    Args:
        role: "user" or "assistant"
        content: Message content
    """
    st.session_state.messages.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })
    logger.debug(f"Added {role} message to history")


def clear_session():
    """Clear current session and start fresh"""
    logger.info(f"Clearing session: {st.session_state.thread_id}")

    _apply_defaults(_session_defaults())

    st.success("Session cleared! Starting fresh.")


def get_session_info() -> dict:
    """Get current session information"""
    return {
        "thread_id": st.session_state.get("thread_id", "N/A"),
        "message_count": len(st.session_state.get("messages", [])),
        "portfolio_size": len(st.session_state.get("portfolio", {})),
        "currency": st.session_state.get("currency", "USD"),
    }
