"""Business logic for pricing and valuation."""
from langchain_core.messages import AIMessage

from src.trading_agent.domain import CurrencyService, PortfolioState, StockPriceProvider
from src.utils.logger import logger


class PortfolioService:
    """Handle market data retrieval, valuation, and currency conversion."""

    def __init__(self, price_provider: StockPriceProvider, currency_service: CurrencyService) -> None:
        self._price_provider = price_provider
        self._currency_service = currency_service

    def fetch_stock_price(self, state: PortfolioState) -> PortfolioState:
        """Load prices for holdings and any pending trade symbol."""
        logger.info("Node: fetch_stock_price")
        try:
            symbols = set(state.get("holdings", {}).keys())
            pending_trade = state.get("pending_trade")
            if pending_trade:
                symbols.add(pending_trade.get("symbol", ""))

            if not symbols:
                state["messages"].append(AIMessage(content="No stocks available for pricing."))
                return state

            prices = self._price_provider.get_batch_prices(list(symbols))
            state["stock_prices"] = prices
            state["messages"].append(AIMessage(content=f"Fetched prices for {len(prices)} stock(s)."))
            return state
        except Exception as exc:  # pragma: no cover - defensive path
            logger.error("Error in fetch_stock_price: %s", exc)
            state["messages"].append(AIMessage(content=f"Error fetching prices: {exc}"))
            return state

    def calculate_portfolio(self, state: PortfolioState) -> PortfolioState:
        """Calculate total portfolio value in USD."""
        logger.info("Node: calculate_portfolio")
        try:
            holdings = state.get("holdings", {})
            prices = state.get("stock_prices", {})
            total_value = 0.0

            for symbol, quantity in holdings.items():
                total_value += quantity * prices.get(symbol, 0.0)

            state["total_value"] = round(total_value, 2)
            state["current_step"] = "calculated"
            state["messages"].append(
                AIMessage(content=f"Current portfolio value (USD): ${state['total_value']:,.2f}")
            )
            return state
        except Exception as exc:  # pragma: no cover - defensive path
            logger.error("Error in calculate_portfolio: %s", exc)
            state["total_value"] = 0.0
            state["messages"].append(AIMessage(content=f"Error calculating portfolio: {exc}"))
            return state

    def convert_currency(self, state: PortfolioState) -> PortfolioState:
        """Convert the USD total to the selected display currency."""
        logger.info("Node: convert_currency")
        try:
            currency = state.get("currency", "USD")
            value_usd = state.get("total_value", 0.0) or 0.0

            if currency == "USD" or value_usd == 0.0:
                return state

            converted = self._currency_service.convert(value_usd, "USD", currency)
            symbol = self._currency_service.get_symbol(currency)
            state["total_value"] = converted
            state["messages"].append(
                AIMessage(content=f"Converted portfolio value to {currency}: {symbol}{converted:,.2f}")
            )
            return state
        except Exception as exc:  # pragma: no cover - defensive path
            logger.error("Error in convert_currency: %s", exc)
            state["messages"].append(AIMessage(content=f"Error converting currency: {exc}"))
            return state
