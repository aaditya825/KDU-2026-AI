"""Compatibility facade for workflow nodes.

New code should import from `src.trading_agent.orchestration.nodes`.
"""
from src.trading_agent.orchestration.nodes import (
    analyze_request,
    calculate_portfolio,
    convert_currency,
    execute_trade,
    fetch_stock_price,
    human_approval_gate,
)

__all__ = [
    "analyze_request",
    "fetch_stock_price",
    "calculate_portfolio",
    "convert_currency",
    "human_approval_gate",
    "execute_trade",
]

