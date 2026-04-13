"""Static currency conversion for the portfolio demo."""
from src.trading_agent.domain import CurrencyService


class StaticCurrencyConverter(CurrencyService):
    """Convert between supported currencies using fixed rates."""

    RATES = {
        "USD": 1.0,
        "INR": 83.12,
        "EUR": 0.92,
    }

    SYMBOLS = {
        "USD": "$",
        "INR": "Rs.",
        "EUR": "EUR ",
    }

    def convert(self, amount: float, from_currency: str, to_currency: str) -> float:
        """Convert an amount between supported currencies."""
        if from_currency not in self.RATES:
            raise ValueError(f"Unsupported source currency: {from_currency}")
        if to_currency not in self.RATES:
            raise ValueError(f"Unsupported target currency: {to_currency}")

        usd_amount = amount / self.RATES[from_currency]
        return round(usd_amount * self.RATES[to_currency], 2)

    def get_symbol(self, currency: str) -> str:
        """Return the display symbol or prefix for a currency."""
        if currency not in self.SYMBOLS:
            raise ValueError(f"Unsupported currency: {currency}")
        return self.SYMBOLS[currency]

    def get_supported_currencies(self) -> list[str]:
        """List currencies supported by the mock converter."""
        return list(self.RATES.keys())


_converter: StaticCurrencyConverter | None = None


def get_currency_service() -> StaticCurrencyConverter:
    """Return a singleton converter for app-wide use."""
    global _converter
    if _converter is None:
        _converter = StaticCurrencyConverter()
    return _converter
