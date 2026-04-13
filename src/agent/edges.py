"""Compatibility facade for workflow routes.

New code should import from `src.trading_agent.orchestration.routes`.
"""
from src.trading_agent.orchestration.routes import (
    route_after_analyze,
    route_after_approval,
    route_after_calculate,
    route_after_execute,
)


def route_after_fetch_prices(_state):
    """Legacy route retained for compatibility."""
    return "calculate_portfolio"


def route_after_convert(_state):
    """Legacy route retained for compatibility."""
    return "end"


__all__ = [
    "route_after_analyze",
    "route_after_fetch_prices",
    "route_after_calculate",
    "route_after_approval",
    "route_after_execute",
    "route_after_convert",
]
