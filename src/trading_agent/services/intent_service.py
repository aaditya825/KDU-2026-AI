"""Business logic for interpreting user requests."""
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from src.trading_agent.domain import CurrencyService, IntentParser, PortfolioState
from src.utils.logger import logger


class IntentService:
    """Interpret the latest user request and update workflow state."""

    def __init__(self, parser: IntentParser, currency_service: CurrencyService) -> None:
        self._parser = parser
        self._currency_service = currency_service

    def analyze_request(self, state: PortfolioState) -> PortfolioState:
        """Parse the latest user message into a workflow action."""
        logger.info("Node: analyze_request")

        try:
            user_messages = [message for message in state["messages"] if isinstance(message, HumanMessage)]
            if not user_messages:
                state["messages"].append(AIMessage(content="No user input found."))
                return state

            user_message = str(user_messages[-1].content)
            decision = self._parser.parse(user_message, state)
            action = decision.action
            params = decision.params

            if state.get("pending_trade"):
                normalized = user_message.strip().lower()
                if normalized in {"approved", "approve", "yes", "confirm"}:
                    action = "approval_response"
                    params = {"approved": True}
                elif normalized in {"rejected", "reject", "no", "cancel"}:
                    action = "approval_response"
                    params = {"approved": False}

            state["current_step"] = action

            if action in {"buy_stock", "sell_stock"}:
                self._apply_trade_request(state, action, params)
            elif action == "approval_response":
                self._apply_approval_decision(state, params)
            elif action == "change_currency":
                self._apply_currency_change(state, params)
            elif action == "view_holdings":
                holdings = state.get("holdings", {})
                summary = ", ".join(f"{symbol}: {qty}" for symbol, qty in holdings.items()) or "No holdings yet."
                state["messages"].append(AIMessage(content=f"Current holdings: {summary}"))
            else:
                state["messages"].append(AIMessage(content=f"Processing request: {action}"))

            logger.info("Intent analysis complete: %s", action)
            return state
        except Exception as exc:  # pragma: no cover - defensive path
            logger.error("Error in analyze_request: %s", exc)
            state["messages"].append(AIMessage(content=f"Error analyzing request: {exc}"))
            return state

    def _apply_trade_request(self, state: PortfolioState, action: str, params: dict[str, Any]) -> None:
        symbol = str(params.get("symbol", "")).upper()
        quantity = int(params.get("quantity", 1))

        state["pending_trade"] = {
            "action": action.replace("_stock", ""),
            "symbol": symbol,
            "quantity": quantity,
        }
        state["requires_approval"] = True
        state["messages"].append(
            AIMessage(content=f"Prepared trade request: {action.replace('_', ' ')} {quantity} {symbol}")
        )

    def _apply_approval_decision(self, state: PortfolioState, params: dict[str, Any]) -> None:
        approved = bool(params.get("approved"))
        state["approval_granted"] = approved
        state["requires_approval"] = False
        state["messages"].append(
            AIMessage(
                content="Approval recorded. Resuming trade workflow."
                if approved
                else "Trade rejected. Pending order has been cancelled."
            )
        )

    def _apply_currency_change(self, state: PortfolioState, params: dict[str, Any]) -> None:
        requested_currency = str(
            params.get("currency") or params.get("target_currency") or params.get("target") or ""
        ).upper()
        supported = set(self._currency_service.get_supported_currencies())

        if requested_currency in supported:
            state["currency"] = requested_currency
            state["messages"].append(AIMessage(content=f"Currency changed to {requested_currency}."))
            return

        state["messages"].append(
            AIMessage(
                content=(
                    f"Unsupported currency '{requested_currency or 'UNKNOWN'}'. "
                    f"Supported currencies: {', '.join(sorted(supported))}"
                )
            )
        )
