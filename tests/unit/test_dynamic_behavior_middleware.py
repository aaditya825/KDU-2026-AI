from assistant.backend.application.services.dynamic_behavior_middleware import (
    DynamicBehaviorMiddleware,
)
from assistant.backend.application.services.input_normalizer import (
    NormalizedAssistantRequest,
)


def test_dynamic_behavior_middleware_applies_route_defaults() -> None:
    middleware = DynamicBehaviorMiddleware()

    result = middleware.apply(
        NormalizedAssistantRequest(
            message="Describe this image",
            session_id="session-1",
            user_id="user-1",
        ),
        route="image_text",
    )

    assert result.communication_style == "neutral"
    assert result.expertise_level == "general"
    assert result.preferred_response_length == "detailed"


def test_dynamic_behavior_middleware_preserves_explicit_frontend_preferences() -> None:
    middleware = DynamicBehaviorMiddleware()

    result = middleware.apply(
        NormalizedAssistantRequest(
            message="Weather in Mumbai",
            session_id="session-1",
            user_id="user-1",
            communication_style="friendly",
            expertise_level="expert",
            preferred_response_length="medium",
        ),
        route="weather_text",
    )

    assert result.communication_style == "friendly"
    assert result.expertise_level == "expert"
    assert result.preferred_response_length == "medium"


def test_dynamic_behavior_middleware_normalizes_invalid_values_to_route_defaults() -> None:
    middleware = DynamicBehaviorMiddleware()

    result = middleware.apply(
        NormalizedAssistantRequest(
            message="Explain this app",
            session_id="session-1",
            user_id="user-1",
            communication_style="unexpected",
            expertise_level="invalid",
            preferred_response_length="verbose",
        ),
        route="general_text",
    )

    assert result.communication_style == "neutral"
    assert result.expertise_level == "general"
    assert result.preferred_response_length == "medium"
