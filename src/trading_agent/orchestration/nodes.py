"""Workflow node handlers that delegate business logic to services."""
from src.trading_agent.bootstrap import get_service_container
from src.trading_agent.domain import PortfolioState


def analyze_request(state: PortfolioState) -> PortfolioState:
    return get_service_container().intent_service.analyze_request(state)


def fetch_stock_price(state: PortfolioState) -> PortfolioState:
    return get_service_container().portfolio_service.fetch_stock_price(state)


def calculate_portfolio(state: PortfolioState) -> PortfolioState:
    return get_service_container().portfolio_service.calculate_portfolio(state)


def convert_currency(state: PortfolioState) -> PortfolioState:
    return get_service_container().portfolio_service.convert_currency(state)


def human_approval_gate(state: PortfolioState) -> PortfolioState:
    return get_service_container().trade_service.prepare_human_approval(state)


def execute_trade(state: PortfolioState) -> PortfolioState:
    return get_service_container().trade_service.execute_trade(state)

