"""Compatibility wrapper for Streamlit backend client."""
from src.trading_agent.ui.backend_client import send_approval, send_chat_message

__all__ = ["send_chat_message", "send_approval"]
