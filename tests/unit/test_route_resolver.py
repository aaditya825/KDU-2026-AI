from assistant.backend.application.services.input_normalizer import NormalizedAssistantRequest
from assistant.backend.application.services.route_resolver import RouteResolver


def test_route_resolver_returns_general_text_for_non_weather_prompt() -> None:
    resolver = RouteResolver()

    route = resolver.resolve(
        NormalizedAssistantRequest(
            message="Explain LCEL in simple terms",
            session_id="session-1",
            user_id="user-1",
        )
    )

    assert route == "general_text"


def test_route_resolver_returns_weather_text_for_weather_prompt() -> None:
    resolver = RouteResolver()

    route = resolver.resolve(
        NormalizedAssistantRequest(
            message="What's the weather in Mumbai today?",
            session_id="session-1",
            user_id="user-1",
        )
    )

    assert route == "weather_text"


def test_route_resolver_returns_image_text_when_request_has_image() -> None:
    resolver = RouteResolver()

    route = resolver.resolve(
        NormalizedAssistantRequest(
            message="Describe this image",
            session_id="session-1",
            user_id="user-1",
            image_bytes=b"img",
            image_mime_type="image/png",
        )
    )

    assert route == "image_text"
