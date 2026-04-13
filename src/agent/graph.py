"""Compatibility facade for graph APIs.

New code should import from `src.trading_agent.orchestration.graph`.
"""
from src.trading_agent.orchestration.graph import (
    create_agent_graph,
    get_graph,
    initialize_state,
    invoke_agent,
)

__all__ = ["create_agent_graph", "get_graph", "invoke_agent", "initialize_state"]

