"""Domain state definitions for the trading workflow."""
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class PortfolioState(TypedDict):
    """State shared across all workflow nodes."""

    holdings: Dict[str, int]
    messages: Annotated[List[BaseMessage], add_messages]
    current_step: str
    total_value: Optional[float]
    currency: str
    stock_prices: Dict[str, float]
    pending_trade: Optional[Dict[str, Any]]
    requires_approval: bool
    approval_granted: Optional[bool]
    thread_id: str
    timestamp: datetime
    value_history: List[Dict[str, Any]]

