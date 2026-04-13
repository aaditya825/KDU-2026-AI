"""Protocols for infrastructure dependencies (DIP)."""
from typing import Dict, List, Protocol

from src.trading_agent.domain.models import IntentDecision
from src.trading_agent.domain.state import PortfolioState


class IntentParser(Protocol):
    """Parse a user message into an intent decision."""

    def parse(self, user_message: str, state: PortfolioState) -> IntentDecision:
        ...


class StockPriceProvider(Protocol):
    """Provide stock prices for one or more symbols."""

    def get_price(self, symbol: str) -> float:
        ...

    def get_batch_prices(self, symbols: List[str]) -> Dict[str, float]:
        ...


class CurrencyService(Protocol):
    """Provide currency conversion and display metadata."""

    def convert(self, amount: float, from_currency: str, to_currency: str) -> float:
        ...

    def get_symbol(self, currency: str) -> str:
        ...

    def get_supported_currencies(self) -> list[str]:
        ...

