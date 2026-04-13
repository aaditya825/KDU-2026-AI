"""Compatibility wrapper for backend service functions."""
from src.trading_agent.api.service import process_approval, process_chat_message

__all__ = ["process_chat_message", "process_approval"]
