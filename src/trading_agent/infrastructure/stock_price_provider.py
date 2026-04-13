"""Mock market data provider."""
import random
from typing import Dict, List

from src.trading_agent.domain import StockPriceProvider
from src.utils.logger import logger


class MockStockPriceProvider(StockPriceProvider):
    """Return realistic-enough stock prices for demos and tests."""

    BASE_PRICES = {
        "AAPL": 175.50,
        "GOOGL": 140.25,
        "MSFT": 380.00,
        "TSLA": 245.30,
        "AMZN": 178.90,
        "META": 485.20,
        "NVDA": 875.40,
        "NFLX": 625.10,
    }

    def __init__(self) -> None:
        self.prices = self.BASE_PRICES.copy()

    def get_price(self, symbol: str) -> float:
        """Return a slightly fluctuating price."""
        if symbol not in self.prices:
            logger.warning("Unknown symbol %s. Returning fallback price.", symbol)
            return 100.0

        base_price = self.prices[symbol]
        fluctuation = random.uniform(-0.03, 0.03)
        return round(base_price * (1 + fluctuation), 2)

    def get_batch_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Return prices for multiple symbols."""
        return {symbol: self.get_price(symbol) for symbol in symbols if symbol}


_provider: MockStockPriceProvider | None = None


def get_stock_price_provider() -> MockStockPriceProvider:
    """Return a singleton provider for the current app process."""
    global _provider
    if _provider is None:
        _provider = MockStockPriceProvider()
    return _provider
