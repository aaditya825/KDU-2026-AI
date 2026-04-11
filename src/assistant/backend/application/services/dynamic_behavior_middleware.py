from dataclasses import replace

from assistant.backend.application.services.input_normalizer import (
    NormalizedAssistantRequest,
)


class DynamicBehaviorMiddleware:
    """Resolve effective request behavior before the use-case layer runs."""

    _allowed_communication_styles = {
        "neutral",
        "friendly",
        "technical",
        "child_friendly",
    }
    _allowed_expertise_levels = {"beginner", "general", "expert"}
    _allowed_response_lengths = {"short", "medium", "detailed"}
    _route_defaults = {
        "general_text": {
            "communication_style": "neutral",
            "expertise_level": "general",
            "preferred_response_length": "medium",
        },
        "weather_text": {
            "communication_style": "neutral",
            "expertise_level": "general",
            "preferred_response_length": "short",
        },
        "image_text": {
            "communication_style": "neutral",
            "expertise_level": "general",
            "preferred_response_length": "detailed",
        },
    }

    def apply(
        self,
        request: NormalizedAssistantRequest,
        *,
        route: str,
    ) -> NormalizedAssistantRequest:
        defaults = self._route_defaults.get(
            route, self._route_defaults["general_text"]
        )
        return replace(
            request,
            communication_style=self._normalize_choice(
                request.communication_style,
                defaults["communication_style"],
                self._allowed_communication_styles,
            ),
            expertise_level=self._normalize_choice(
                request.expertise_level,
                defaults["expertise_level"],
                self._allowed_expertise_levels,
            ),
            preferred_response_length=self._normalize_choice(
                request.preferred_response_length,
                defaults["preferred_response_length"],
                self._allowed_response_lengths,
            ),
        )

    def _normalize_choice(
        self,
        value: str | None,
        default: str,
        allowed_values: set[str],
    ) -> str:
        normalized = (value or "").strip().lower()
        return normalized if normalized in allowed_values else default
