"""Application service for trade approval and execution."""
from datetime import datetime

from langchain_core.messages import AIMessage

from src.trading_agent.domain import PortfolioState
from src.utils.logger import logger


class TradeService:
    """Manage trade approval messaging and stateful trade execution."""

    def prepare_human_approval(self, state: PortfolioState) -> PortfolioState:
        """Build and append trade approval prompt."""
        logger.info("Node: human_approval_gate")
        try:
            trade = state.get("pending_trade")
            if not trade:
                logger.warning("No pending trade to approve")
                return state

            symbol = trade.get("symbol", "UNKNOWN")
            quantity = trade.get("quantity", 0)
            action = trade.get("action", "trade").upper()
            price = state.get("stock_prices", {}).get(symbol, 0.0)
            total_cost = round(quantity * price, 2)

            approval_msg = (
                "⚠️ **Approval Required**\n\n"
                f"**Action:** {action}\n"
                f"**Symbol:** {symbol}\n"
                f"**Quantity:** {quantity} shares\n"
                f"**Price:** ${price:.2f}/share\n"
                f"**Total:** ${total_cost:,.2f}\n\n"
                "Please approve or reject this trade."
            )
            state["requires_approval"] = True
            state["messages"].append(AIMessage(content=approval_msg))
            logger.info(f"Trade pending approval: {action} {quantity} {symbol}")
            return state
        except Exception as exc:
            logger.error(f"Error in human_approval_gate: {exc}")
            state["messages"].append(AIMessage(content=f"Error preparing approval: {exc}"))
            return state

    def execute_trade(self, state: PortfolioState) -> PortfolioState:
        """Execute pending buy/sell based on approval state."""
        logger.info("Node: execute_trade")
        try:
            if not state.get("approval_granted"):
                state["messages"].append(AIMessage(content="❌ Trade cancelled by user"))
                state["pending_trade"] = None
                state["requires_approval"] = False
                logger.info("Trade rejected by user")
                return state

            trade = state.get("pending_trade")
            if not trade:
                logger.warning("No pending trade to execute")
                return state

            symbol = trade.get("symbol", "").upper()
            quantity = int(trade.get("quantity", 0))
            action = trade.get("action", "buy")
            holdings = state.get("holdings", {})
            current_qty = holdings.get(symbol, 0)

            if action == "buy":
                new_qty = current_qty + quantity
                action_msg = f"bought {quantity} shares of {symbol}"
            elif action == "sell":
                if current_qty < quantity:
                    state["messages"].append(
                        AIMessage(content=f"❌ Cannot sell {quantity} {symbol}: only {current_qty} in portfolio")
                    )
                    state["pending_trade"] = None
                    state["requires_approval"] = False
                    state["approval_granted"] = None
                    return state
                new_qty = current_qty - quantity
                action_msg = f"sold {quantity} shares of {symbol}"
            else:
                logger.error(f"Unknown action: {action}")
                return state

            if new_qty > 0:
                holdings[symbol] = new_qty
            elif symbol in holdings:
                del holdings[symbol]

            state["holdings"] = holdings

            value_history = state.get("value_history", [])
            value_history.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "value": state.get("total_value", 0.0),
                    "action": f"{action} {quantity} {symbol}",
                }
            )
            state["value_history"] = value_history
            state["messages"].append(AIMessage(content=f"✅ Trade executed successfully: {action_msg}"))

            state["pending_trade"] = None
            state["requires_approval"] = False
            state["approval_granted"] = None

            logger.info(f"Trade executed: {action_msg}")
            logger.info(f"New holdings: {holdings}")
            return state
        except Exception as exc:
            logger.error(f"Error in execute_trade: {exc}")
            state["messages"].append(AIMessage(content=f"Error executing trade: {exc}"))
            return state

