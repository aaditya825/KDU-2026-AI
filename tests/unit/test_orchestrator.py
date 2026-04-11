from assistant.backend.application.services.dynamic_behavior_middleware import (
    DynamicBehaviorMiddleware,
)
from assistant.backend.application.services.input_normalizer import InputNormalizer
from assistant.backend.application.services.response_formatter import ResponseFormatter
from assistant.backend.application.services.route_resolver import RouteResolver
from assistant.backend.contracts.responses import GeneralTextResult, ImageTextResult
from assistant.backend.contracts.requests import AssistantChatRequest
from assistant.backend.orchestrator.assistant_orchestrator import AssistantOrchestrator


def test_orchestrator_returns_text_response() -> None:
    class StubTextChatUseCase:
        def execute(self, request):
            return GeneralTextResult(answer=f"Echo: {request.message}")

    class StubWeatherChatUseCase:
        def execute(self, request):
            raise AssertionError("weather use case should not run for a general text prompt")

    class StubImageChatUseCase:
        def execute(self, request):
            raise AssertionError("image use case should not run for a general text prompt")

    class StubModelSelector:
        def active_model_name(self) -> str:
            return "gemini-2.5-flash"

    orchestrator = AssistantOrchestrator(
        input_normalizer=InputNormalizer(),
        route_resolver=RouteResolver(),
        dynamic_behavior_middleware=DynamicBehaviorMiddleware(),
        text_chat_use_case=StubTextChatUseCase(),
        weather_chat_use_case=StubWeatherChatUseCase(),
        image_chat_use_case=StubImageChatUseCase(),
        response_formatter=ResponseFormatter(),
        model_selector=StubModelSelector(),
    )

    response = orchestrator.execute(
        AssistantChatRequest(
            message="What is this app?",
            session_id="test-session",
            user_id="test-user",
        )
    )

    assert response.route == "general_text"
    assert response.model == "gemini-2.5-flash"
    assert "What is this app?" in response.answer


def test_orchestrator_routes_image_request_to_image_use_case() -> None:
    class StubTextChatUseCase:
        def execute(self, request):
            raise AssertionError("text use case should not run for an image prompt")

    class StubWeatherChatUseCase:
        def execute(self, request):
            raise AssertionError("weather use case should not run for an image prompt")

    class StubImageChatUseCase:
        def execute(self, request):
            return ImageTextResult(
                answer="A desk setup is visible.",
                description="A laptop on a desk beside a coffee mug.",
                objects=["laptop", "desk", "coffee mug"],
                summary="Indoor workspace scene.",
            )

    class StubModelSelector:
        def active_model_name(self) -> str:
            return "gemini-2.5-flash"

    orchestrator = AssistantOrchestrator(
        input_normalizer=InputNormalizer(),
        route_resolver=RouteResolver(),
        dynamic_behavior_middleware=DynamicBehaviorMiddleware(),
        text_chat_use_case=StubTextChatUseCase(),
        weather_chat_use_case=StubWeatherChatUseCase(),
        image_chat_use_case=StubImageChatUseCase(),
        response_formatter=ResponseFormatter(),
        model_selector=StubModelSelector(),
    )

    response = orchestrator.execute(
        AssistantChatRequest(
            message="Describe this image",
            session_id="test-session",
            user_id="test-user",
            image_base64="aW1hZ2U=",
            image_mime_type="image/png",
        )
    )

    assert response.route == "image_text"
    assert response.objects == ["laptop", "desk", "coffee mug"]


def test_orchestrator_applies_route_aware_behavior_defaults_before_use_case_execution() -> None:
    class CapturingWeatherUseCase:
        def __init__(self) -> None:
            self.last_request = None

        def execute(self, request):
            self.last_request = request
            return GeneralTextResult(answer="stubbed weather answer")

    class StubTextChatUseCase:
        def execute(self, request):
            raise AssertionError("text use case should not run for a weather prompt")

    class StubImageChatUseCase:
        def execute(self, request):
            raise AssertionError("image use case should not run for a weather prompt")

    class StubModelSelector:
        def active_model_name(self) -> str:
            return "gemini-2.5-flash-lite"

    weather_use_case = CapturingWeatherUseCase()
    orchestrator = AssistantOrchestrator(
        input_normalizer=InputNormalizer(),
        route_resolver=RouteResolver(),
        dynamic_behavior_middleware=DynamicBehaviorMiddleware(),
        text_chat_use_case=StubTextChatUseCase(),
        weather_chat_use_case=weather_use_case,
        image_chat_use_case=StubImageChatUseCase(),
        response_formatter=ResponseFormatter(),
        model_selector=StubModelSelector(),
    )

    orchestrator.execute(
        AssistantChatRequest(
            message="What is the weather in Delhi today?",
            session_id="test-session",
            user_id="test-user",
        )
    )

    assert weather_use_case.last_request.communication_style == "neutral"
    assert weather_use_case.last_request.expertise_level == "general"
    assert weather_use_case.last_request.preferred_response_length == "short"
