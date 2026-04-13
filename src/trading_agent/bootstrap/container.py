"""Dependency composition root for the trading agent."""
from dataclasses import dataclass

from src.trading_agent.infrastructure import (
    GeminiIntentParser,
    LangSmithClient,
    get_currency_service,
    get_stock_price_provider,
)
from src.trading_agent.services import (
    IntentService,
    ObservabilityService,
    PortfolioService,
    TradeService,
)


@dataclass(frozen=True)
class ServiceContainer:
    """Resolved service graph for node execution."""

    intent_service: IntentService
    portfolio_service: PortfolioService
    trade_service: TradeService
    observability_service: ObservabilityService


_container: ServiceContainer | None = None


def get_service_container() -> ServiceContainer:
    """Create singleton service container."""
    global _container
    if _container is None:
        currency_service = get_currency_service()
        price_provider = get_stock_price_provider()
        parser = GeminiIntentParser()
        _container = ServiceContainer(
            intent_service=IntentService(parser=parser, currency_service=currency_service),
            portfolio_service=PortfolioService(
                price_provider=price_provider,
                currency_service=currency_service,
            ),
            trade_service=TradeService(),
            observability_service=ObservabilityService(client=LangSmithClient()),
        )
    return _container
