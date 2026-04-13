"""Workflow routing functions (pure control-flow decisions)."""
from src.trading_agent.domain import PortfolioState
from src.utils.logger import logger


def route_after_analyze(state: PortfolioState) -> str:
    """Route after request analysis."""
    action = state.get("current_step", "help")
    logger.info(f"Route after analyze: {action}")

    if action in {"calculate_portfolio", "buy_stock", "sell_stock"}:
        return "fetch_stock_price"
    if action == "approval_response":
        return "calculate_portfolio"
    if action == "change_currency":
        return "fetch_stock_price"
    if action in {"view_holdings", "help"}:
        return "end"
    return "end"


def route_after_calculate(state: PortfolioState) -> str:
    """Route after valuation calculation."""
    currency = state.get("currency", "USD")
    pending_trade = state.get("pending_trade")
    approval_granted = state.get("approval_granted")

    if pending_trade:
        if approval_granted is None:
            logger.info("Route after calculate: pending trade requires approval")
            return "human_approval_gate"
        logger.info("Route after calculate: approval decision found, executing trade")
        return "execute_trade"

    if currency != "USD":
        logger.info(f"Route after calculate: convert to {currency}")
        return "convert_currency"

    logger.info("Route after calculate: finished")
    return "end"


def route_after_approval(state: PortfolioState) -> str:
    """Route after approval pause."""
    logger.info("Route after approval: execute_trade")
    return "execute_trade"


def route_after_execute(state: PortfolioState) -> str:
    """Route after trade execution."""
    currency = state.get("currency", "USD")
    if currency != "USD":
        logger.info(f"Route after execute: convert to {currency}")
        return "convert_currency"
    logger.info("Route after execute: finished")
    return "end"
