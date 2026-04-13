"""Mock market data provider."""
import random
from typing import Dict, List

from src.trading_agent.domain import StockPriceProvider
from src.utils.logger import logger


class MockStockPriceProvider(StockPriceProvider):
    """Provide deterministic-looking stock prices for local runs and tests."""

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
        logger.info(f"Stock simulator initialized with {len(self.prices)} stocks")

    def get_price(self, symbol: str) -> float:
        if symbol not in self.prices:
            logger.warning(f"Symbol {symbol} not found, returning base price of $100")
            return 100.0

        base = self.prices[symbol]
        fluctuation = random.uniform(-0.03, 0.03)
        return round(base * (1 + fluctuation), 2)

    def get_batch_prices(self, symbols: List[str]) -> Dict[str, float]:
        prices = {symbol: self.get_price(symbol) for symbol in symbols if symbol}
        logger.info(f"Fetched prices for {len(prices)} symbols")
        return prices

    def add_symbol(self, symbol: str, price: float) -> None:
        self.prices[symbol] = price
        logger.info(f"Added/updated symbol {symbol} with base price ${price}")

    def get_available_symbols(self) -> List[str]:
        return list(self.prices.keys())


_provider: MockStockPriceProvider | None = None


def get_stock_price_provider() -> MockStockPriceProvider:
    """Return singleton provider for app lifecycle consistency."""
    global _provider
    if _provider is None:
        _provider = MockStockPriceProvider()
    return _provider

