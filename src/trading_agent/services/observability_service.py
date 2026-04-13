"""Business-facing observability helpers."""
from typing import Any

from src.trading_agent.infrastructure.langsmith_client import LangSmithClient


class ObservabilityService:
    """Build a compact observability summary for each interaction."""

    def __init__(self, client: LangSmithClient) -> None:
        self._client = client

    def summarize_interaction(
        self,
        *,
        thread_id: str,
        user_message: str,
        assistant_message: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Estimate usage and expose tracing metadata for the latest interaction."""
        return self._client.build_observation(
            thread_id=thread_id,
            user_message=user_message,
            assistant_message=assistant_message,
            metadata=metadata or {},
        )
