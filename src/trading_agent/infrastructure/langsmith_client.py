"""Helpers for LangSmith tracing metadata and usage estimation."""
from typing import Any

from src.config.settings import settings


class LangSmithClient:
    """Build lightweight tracing summaries around LangSmith-enabled runs."""

    _MODEL_NAME = "gemini-1.5-pro"
    _MODEL_PRICING = {
        "gemini-1.5-pro": {
            "input_per_1k_tokens": 0.00125,
            "output_per_1k_tokens": 0.005,
        }
    }

    def build_observation(
        self,
        *,
        thread_id: str,
        user_message: str,
        assistant_message: str | None,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Estimate tokens and cost for a single interaction."""
        input_tokens = self._estimate_tokens(user_message)
        output_tokens = self._estimate_tokens(assistant_message or "")
        total_tokens = input_tokens + output_tokens
        estimated_cost = self._estimate_cost(input_tokens, output_tokens)

        return {
            "thread_id": thread_id,
            "tracing_enabled": bool(settings.langsmith_api_key and settings.langchain_tracing_v2),
            "project": settings.langsmith_project,
            "model": self._MODEL_NAME,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": round(estimated_cost, 6),
            "metadata": metadata,
        }

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Very rough token estimate suitable for dashboards and tests."""
        stripped = text.strip()
        if not stripped:
            return 0
        return max(1, round(len(stripped.split()) * 1.3))

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        pricing = self._MODEL_PRICING[self._MODEL_NAME]
        input_cost = (input_tokens / 1000) * pricing["input_per_1k_tokens"]
        output_cost = (output_tokens / 1000) * pricing["output_per_1k_tokens"]
        return input_cost + output_cost
