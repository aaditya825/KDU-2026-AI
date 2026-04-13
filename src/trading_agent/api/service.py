"""Service layer used by the FastAPI routes."""
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from src.trading_agent.api.schemas import AgentResponse, FrontendStatePayload
from src.trading_agent.bootstrap import get_service_container
from src.trading_agent.orchestration.graph import initialize_state, invoke_agent


def _latest_ai_message(messages: list[Any]) -> str | None:
    """Return the latest assistant message from the workflow state."""
    for message in reversed(messages or []):
        if isinstance(message, AIMessage) and message.content:
            return str(message.content)
    return None


def _approval_message(result: dict[str, Any]) -> str | None:
    """Build a useful assistant message while the graph is paused for approval."""
    if not result.get("requires_approval"):
        return None

    trade = result.get("pending_trade") or {}
    symbol = trade.get("symbol")
    quantity = trade.get("quantity")
    action = str(trade.get("action", "trade")).upper()
    if not symbol or quantity is None:
        return "Approval required before executing the pending trade."

    price = (result.get("stock_prices") or {}).get(symbol, 0.0)
    total_cost = float(quantity) * float(price)
    return (
        "Approval required.\n"
        f"Action: {action}\n"
        f"Symbol: {symbol}\n"
        f"Quantity: {quantity} shares\n"
        f"Price: ${price:.2f} per share\n"
        f"Total: ${total_cost:,.2f}"
    )


def _assistant_message(result: dict[str, Any]) -> str | None:
    """Return the most useful assistant message for API consumers."""
    return _approval_message(result) or _latest_ai_message(result.get("messages", []))


def _build_observability(thread_id: str, user_message: str, result: dict[str, Any]) -> dict[str, Any]:
    assistant_message = _assistant_message(result)
    return get_service_container().observability_service.summarize_interaction(
        thread_id=thread_id,
        user_message=user_message,
        assistant_message=assistant_message,
        metadata={
            "current_step": result.get("current_step"),
            "requires_approval": bool(result.get("requires_approval")),
            "currency": result.get("currency", "USD"),
        },
    )


def _to_response(result: dict[str, Any], observability: dict[str, Any] | None = None) -> AgentResponse:
    """Normalize raw graph output into the API response model."""
    return AgentResponse(
        holdings=result.get("holdings", {}),
        stock_prices=result.get("stock_prices", {}),
        value_history=result.get("value_history", []),
        total_value=result.get("total_value"),
        currency=result.get("currency", "USD"),
        pending_trade=result.get("pending_trade"),
        requires_approval=bool(result.get("requires_approval")),
        approval_granted=result.get("approval_granted"),
        assistant_message=_assistant_message(result),
        observability=observability or {},
    )


def process_chat_message(thread_id: str, message: str, frontend_state: FrontendStatePayload) -> AgentResponse:
    """Run a single user message through the graph."""
    state = initialize_state(thread_id, seed_portfolio=frontend_state.holdings)
    state["messages"] = [HumanMessage(content=message)]
    state["holdings"] = frontend_state.holdings
    state["currency"] = frontend_state.currency
    state["stock_prices"] = frontend_state.stock_prices
    state["value_history"] = frontend_state.value_history
    state["pending_trade"] = frontend_state.pending_trade
    state["requires_approval"] = frontend_state.requires_approval
    state["approval_granted"] = frontend_state.approval_granted

    result = invoke_agent(state, thread_id)
    observability = _build_observability(thread_id, message, result)
    return _to_response(result, observability)


def refresh_portfolio_snapshot(thread_id: str, frontend_state: FrontendStatePayload) -> AgentResponse:
    """Refresh prices and valuation without adding visible chat noise."""
    state = initialize_state(thread_id, seed_portfolio=frontend_state.holdings)
    state["holdings"] = frontend_state.holdings
    state["currency"] = frontend_state.currency
    state["stock_prices"] = frontend_state.stock_prices
    state["value_history"] = frontend_state.value_history
    state["pending_trade"] = frontend_state.pending_trade
    state["requires_approval"] = frontend_state.requires_approval
    state["approval_granted"] = frontend_state.approval_granted

    container = get_service_container()
    state = container.portfolio_service.fetch_stock_price(state)
    state = container.portfolio_service.calculate_portfolio(state)
    if state.get("currency") != "USD":
        state = container.portfolio_service.convert_currency(state)

    observability = _build_observability(thread_id, "refresh_snapshot", state)
    return _to_response(state, observability)


def process_approval(thread_id: str, approved: bool) -> AgentResponse:
    """Resume a paused graph with an approval decision."""
    result = invoke_agent(
        Command(update={"approval_granted": approved}, resume=True),
        thread_id,
    )
    observability = _build_observability(thread_id, f"approval={approved}", result)
    return _to_response(result, observability)
