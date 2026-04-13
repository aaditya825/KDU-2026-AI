"""Application service for pricing and valuation."""
from langchain_core.messages import AIMessage

from src.trading_agent.domain import CurrencyService, PortfolioState, StockPriceProvider
from src.utils.logger import logger


class PortfolioService:
    """Handle market data retrieval and portfolio valuation."""

    def __init__(self, price_provider: StockPriceProvider, currency_service: CurrencyService) -> None:
        self._price_provider = price_provider
        self._currency_service = currency_service

    def fetch_stock_price(self, state: PortfolioState) -> PortfolioState:
        """Populate latest stock prices for holdings and pending trade."""
        logger.info("Node: fetch_stock_price")
        try:
            symbols = set(state.get("holdings", {}).keys())
            pending_trade = state.get("pending_trade")
            if pending_trade:
                symbols.add(pending_trade.get("symbol", ""))

            if symbols:
                prices = self._price_provider.get_batch_prices(list(symbols))
                state["stock_prices"] = prices
                state["messages"].append(AIMessage(content=f"Fetched prices for {len(symbols)} stock(s)"))
                logger.info(f"Fetched prices for: {list(symbols)}")
            else:
                state["messages"].append(AIMessage(content="No stocks to fetch prices for"))
            return state
        except Exception as exc:
            logger.error(f"Error in fetch_stock_price: {exc}")
            state["messages"].append(AIMessage(content=f"Error fetching prices: {exc}"))
            return state

    def calculate_portfolio(self, state: PortfolioState) -> PortfolioState:
        """Calculate total portfolio value in USD."""
        logger.info("Node: calculate_portfolio")
        try:
            total = 0.0
            holdings = state.get("holdings", {})
            prices = state.get("stock_prices", {})

            for symbol, quantity in holdings.items():
                price = prices.get(symbol, 0.0)
                value = quantity * price
                total += value
                logger.debug(f"  {symbol}: {quantity} @ ${price} = ${value}")

            state["total_value"] = round(total, 2)
            state["current_step"] = "calculated"
            logger.info(f"Portfolio total value: ${total}")
            return state
        except Exception as exc:
            logger.error(f"Error in calculate_portfolio: {exc}")
            state["total_value"] = 0.0
            return state

    def convert_currency(self, state: PortfolioState) -> PortfolioState:
        """Convert USD portfolio value to selected currency."""
        logger.info("Node: convert_currency")
        try:
            currency = state.get("currency", "USD")
            if currency == "USD":
                logger.info("No conversion needed (currency is USD)")
                return state

            value_usd = state.get("total_value", 0.0)
            if not value_usd:
                logger.info("No value to convert")
                return state

            converted = self._currency_service.convert(value_usd, "USD", currency)
            state["total_value"] = converted
            symbol = self._currency_service.get_symbol(currency)
            state["messages"].append(
                AIMessage(content=f"Converted to {currency} ({symbol}): {symbol}{converted:,.2f}")
            )
            logger.info(f"Converted ${value_usd} to {symbol}{converted}")
            return state
        except Exception as exc:
            logger.error(f"Error in convert_currency: {exc}")
            state["messages"].append(AIMessage(content=f"Error converting currency: {exc}"))
            return state

