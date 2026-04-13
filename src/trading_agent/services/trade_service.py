"""Business logic for trade approvals and execution."""
from datetime import datetime

from langchain_core.messages import AIMessage

from src.trading_agent.domain import PortfolioState
from src.utils.logger import logger


class TradeService:
    """Manage approval prompts and apply trade operations."""

    def prepare_human_approval(self, state: PortfolioState) -> PortfolioState:
        """Append approval details for a pending trade."""
        logger.info("Node: human_approval_gate")
        try:
            trade = state.get("pending_trade")
            if not trade:
                return state

            symbol = trade.get("symbol", "UNKNOWN")
            quantity = int(trade.get("quantity", 0))
            action = str(trade.get("action", "trade")).upper()
            price = state.get("stock_prices", {}).get(symbol, 0.0)
            total_cost = round(quantity * price, 2)

            state["requires_approval"] = True
            state["messages"].append(
                AIMessage(
                    content=(
                        "Approval required.\n"
                        f"Action: {action}\n"
                        f"Symbol: {symbol}\n"
                        f"Quantity: {quantity} shares\n"
                        f"Price: ${price:.2f} per share\n"
                        f"Total: ${total_cost:,.2f}\n"
                        "Please approve or reject this trade."
                    )
                )
            )
            return state
        except Exception as exc:  # pragma: no cover - defensive path
            logger.error("Error in human_approval_gate: %s", exc)
            state["messages"].append(AIMessage(content=f"Error preparing approval: {exc}"))
            return state

    def execute_trade(self, state: PortfolioState) -> PortfolioState:
        """Apply a pending trade when approval is granted."""
        logger.info("Node: execute_trade")
        try:
            if not state.get("approval_granted"):
                state["messages"].append(AIMessage(content="Trade cancelled by user."))
                state["pending_trade"] = None
                state["requires_approval"] = False
                return state

            trade = state.get("pending_trade")
            if not trade:
                return state

            symbol = str(trade.get("symbol", "")).upper()
            quantity = int(trade.get("quantity", 0))
            action = str(trade.get("action", "buy"))

            holdings = state.get("holdings", {})
            current_qty = int(holdings.get(symbol, 0))

            if action == "buy":
                holdings[symbol] = current_qty + quantity
                action_message = f"Bought {quantity} shares of {symbol}."
            elif action == "sell":
                if current_qty < quantity:
                    state["messages"].append(
                        AIMessage(
                            content=f"Cannot sell {quantity} shares of {symbol}. Current holding: {current_qty}."
                        )
                    )
                    state["pending_trade"] = None
                    state["requires_approval"] = False
                    state["approval_granted"] = None
                    return state

                new_qty = current_qty - quantity
                if new_qty > 0:
                    holdings[symbol] = new_qty
                else:
                    holdings.pop(symbol, None)
                action_message = f"Sold {quantity} shares of {symbol}."
            else:
                state["messages"].append(AIMessage(content=f"Unknown trade action: {action}"))
                return state

            state["holdings"] = holdings
            state["total_value"] = round(
                sum(qty * state.get("stock_prices", {}).get(stock, 0.0) for stock, qty in holdings.items()),
                2,
            )
            state["value_history"].append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "value": state.get("total_value", 0.0),
                    "action": f"{action} {quantity} {symbol}",
                }
            )
            state["messages"].append(AIMessage(content=action_message))
            state["pending_trade"] = None
            state["requires_approval"] = False
            state["approval_granted"] = None
            return state
        except Exception as exc:  # pragma: no cover - defensive path
            logger.error("Error in execute_trade: %s", exc)
            state["messages"].append(AIMessage(content=f"Error executing trade: {exc}"))
            return state
