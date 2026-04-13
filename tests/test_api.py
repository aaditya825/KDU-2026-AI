"""API service regression tests."""
from src.trading_agent.api.schemas import FrontendStatePayload
from src.trading_agent.api.service import process_chat_message


def test_process_chat_message_returns_total_value() -> None:
    """Portfolio valuation should be exposed directly in the API response."""
    response = process_chat_message(
        thread_id="api-value",
        message="What is my portfolio worth?",
        frontend_state=FrontendStatePayload(holdings={"AAPL": 3}),
    )

    assert response.total_value is not None
    assert response.total_value > 0
    assert "portfolio value" in (response.assistant_message or "").lower()


def test_process_chat_message_returns_approval_prompt() -> None:
    """Buy requests should return a meaningful approval message while paused."""
    response = process_chat_message(
        thread_id="api-buy",
        message="Buy 2 TSLA",
        frontend_state=FrontendStatePayload(),
    )

    assert response.requires_approval is True
    assert response.pending_trade is not None
    assert "approval required" in (response.assistant_message or "").lower()
