"""Compatibility facade for workflow state definition.

New code should import from `src.trading_agent.domain.state`.
"""
from src.trading_agent.domain.state import PortfolioState

__all__ = ["PortfolioState"]

