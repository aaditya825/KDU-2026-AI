"""FastAPI application entry point."""
from fastapi import FastAPI

from src.trading_agent.api.schemas import AgentResponse, ApprovalRequest, ChatRequest, SnapshotRequest
from src.trading_agent.api.service import process_approval, process_chat_message, refresh_portfolio_snapshot

app = FastAPI(title="Stock Trading Agent Backend", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Health-check endpoint."""
    return {"status": "ok"}


@app.post("/api/chat", response_model=AgentResponse)
def chat(request: ChatRequest) -> AgentResponse:
    """Process a user chat message."""
    return process_chat_message(
        thread_id=request.thread_id,
        message=request.message,
        frontend_state=request.frontend_state,
    )


@app.post("/api/approval", response_model=AgentResponse)
def approval(request: ApprovalRequest) -> AgentResponse:
    """Resume a paused graph with an approval or rejection."""
    return process_approval(thread_id=request.thread_id, approved=request.approved)


@app.post("/api/portfolio/refresh", response_model=AgentResponse)
def portfolio_refresh(request: SnapshotRequest) -> AgentResponse:
    """Refresh prices and valuation for the dashboard."""
    return refresh_portfolio_snapshot(
        thread_id=request.thread_id,
        frontend_state=request.frontend_state,
    )
