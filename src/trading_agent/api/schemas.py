"""API request and response models."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FrontendStatePayload(BaseModel):
    """Subset of frontend state required to continue a workflow."""

    holdings: Dict[str, int] = Field(default_factory=dict)
    currency: str = "USD"
    stock_prices: Dict[str, float] = Field(default_factory=dict)
    value_history: List[Dict[str, Any]] = Field(default_factory=list)
    pending_trade: Optional[Dict[str, Any]] = None
    requires_approval: bool = False
    approval_granted: Optional[bool] = None


class ChatRequest(BaseModel):
    """Chat interaction request."""

    thread_id: str
    message: str
    frontend_state: FrontendStatePayload = Field(default_factory=FrontendStatePayload)


class ApprovalRequest(BaseModel):
    """Approval decision request."""

    thread_id: str
    approved: bool


class SnapshotRequest(BaseModel):
    """Silent portfolio refresh request for the dashboard."""

    thread_id: str
    frontend_state: FrontendStatePayload = Field(default_factory=FrontendStatePayload)


class AgentResponse(BaseModel):
    """Normalized response returned to the frontend."""

    holdings: Dict[str, int] = Field(default_factory=dict)
    stock_prices: Dict[str, float] = Field(default_factory=dict)
    value_history: List[Dict[str, Any]] = Field(default_factory=list)
    total_value: Optional[float] = None
    currency: str = "USD"
    pending_trade: Optional[Dict[str, Any]] = None
    requires_approval: bool = False
    approval_granted: Optional[bool] = None
    assistant_message: Optional[str] = None
    observability: Dict[str, Any] = Field(default_factory=dict)
