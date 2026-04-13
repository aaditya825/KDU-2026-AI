"""HTTP client used by the Streamlit frontend."""
import os
from typing import Any, Dict

import requests

BACKEND_BASE_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
TIMEOUT_SECONDS = 30


def send_chat_message(thread_id: str, message: str, frontend_state: Dict[str, Any]) -> Dict[str, Any]:
    """Send a user message to the backend."""
    response = requests.post(
        f"{BACKEND_BASE_URL}/api/chat",
        json={
            "thread_id": thread_id,
            "message": message,
            "frontend_state": frontend_state,
        },
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def send_approval(thread_id: str, approved: bool) -> Dict[str, Any]:
    """Send an approval decision to the backend."""
    response = requests.post(
        f"{BACKEND_BASE_URL}/api/approval",
        json={"thread_id": thread_id, "approved": approved},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def refresh_portfolio_snapshot(thread_id: str, frontend_state: Dict[str, Any]) -> Dict[str, Any]:
    """Refresh holdings pricing and valuation without a visible chat command."""
    response = requests.post(
        f"{BACKEND_BASE_URL}/api/portfolio/refresh",
        json={
            "thread_id": thread_id,
            "frontend_state": frontend_state,
        },
        timeout=TIMEOUT_SECONDS,
    )
    if response.status_code == 404:
        return send_chat_message(
            thread_id=thread_id,
            message="What is my portfolio worth?",
            frontend_state=frontend_state,
        )
    response.raise_for_status()
    return response.json()
