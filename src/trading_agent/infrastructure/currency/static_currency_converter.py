"""Static exchange-rate currency service."""
from src.trading_agent.domain import CurrencyService
from src.utils.logger import logger


class StaticCurrencyConverter(CurrencyService):
    """Convert between supported currencies using fixed exchange rates."""

    RATES = {
        "USD": 1.0,
        "INR": 83.12,
        "EUR": 0.92,
    }

    SYMBOLS = {
        "USD": "$",
        "INR": "₹",
        "EUR": "€",
    }

    def convert(self, amount: float, from_currency: str, to_currency: str) -> float:
        if from_currency not in self.RATES:
            raise ValueError(f"Unsupported source currency: {from_currency}")
        if to_currency not in self.RATES:
            raise ValueError(f"Unsupported target currency: {to_currency}")

        usd_amount = amount / self.RATES[from_currency]
        result = usd_amount * self.RATES[to_currency]
        logger.debug(f"Converted {amount} {from_currency} to {result} {to_currency}")
        return round(result, 2)

    def get_symbol(self, currency: str) -> str:
        if currency not in self.SYMBOLS:
            raise ValueError(f"Unsupported currency: {currency}")
        return self.SYMBOLS[currency]

    def get_supported_currencies(self) -> list[str]:
        return list(self.RATES.keys())


_converter: StaticCurrencyConverter | None = None


def get_currency_service() -> StaticCurrencyConverter:
    """Return singleton converter for app lifecycle consistency."""
    global _converter
    if _converter is None:
        _converter = StaticCurrencyConverter()
    return _converter

