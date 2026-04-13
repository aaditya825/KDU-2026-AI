"""Compatibility wrapper for currency conversion."""
from src.trading_agent.infrastructure.currency_converter import StaticCurrencyConverter, get_currency_service


class CurrencyConverter(StaticCurrencyConverter):
    """Legacy class name compatibility."""

    def get_exchange_rate(self, from_currency: str, to_currency: str) -> float:
        if from_currency not in self.RATES:
            raise ValueError(f"Unsupported source currency: {from_currency}")
        if to_currency not in self.RATES:
            raise ValueError(f"Unsupported target currency: {to_currency}")

        in_usd = 1 / self.RATES[from_currency]
        return round(in_usd * self.RATES[to_currency], 4)


_converter: CurrencyConverter | None = None


def get_converter() -> CurrencyConverter:
    """Return converter singleton using the new infrastructure module."""
    global _converter
    if _converter is None:
        service = get_currency_service()
        _converter = CurrencyConverter()
        _converter.RATES = service.RATES
        _converter.SYMBOLS = service.SYMBOLS
    return _converter


__all__ = ["CurrencyConverter", "get_converter"]
