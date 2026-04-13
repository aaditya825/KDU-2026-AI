"""Compatibility wrapper for the stock simulator."""
from src.trading_agent.infrastructure.stock_price_provider import (
    MockStockPriceProvider as StockSimulator,
    get_stock_price_provider,
)


def get_simulator() -> StockSimulator:
    """Return stock price provider singleton (legacy API)."""
    return get_stock_price_provider()


__all__ = ["StockSimulator", "get_simulator"]
