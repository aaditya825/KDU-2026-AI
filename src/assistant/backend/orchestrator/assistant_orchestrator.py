from assistant.backend.application.services.input_normalizer import InputNormalizer
from assistant.backend.application.services.dynamic_behavior_middleware import (
    DynamicBehaviorMiddleware,
)
from assistant.backend.application.services.response_formatter import ResponseFormatter
from assistant.backend.application.services.route_resolver import RouteResolver
from assistant.backend.application.use_cases.image_chat import ImageChatUseCase
from assistant.backend.application.use_cases.text_chat import TextChatUseCase
from assistant.backend.application.use_cases.weather_chat import WeatherChatUseCase
from assistant.backend.contracts.requests import AssistantChatRequest
from assistant.backend.contracts.responses import AssistantResponse
from assistant.backend.shared.exceptions import UnsupportedRouteError


class AssistantOrchestrator:
    """Backend entry point coordinating the active assistant request flow."""

    def __init__(
        self,
        input_normalizer: InputNormalizer,
        route_resolver: RouteResolver,
        dynamic_behavior_middleware: DynamicBehaviorMiddleware,
        text_chat_use_case: TextChatUseCase,
        weather_chat_use_case: WeatherChatUseCase,
        image_chat_use_case: ImageChatUseCase,
        response_formatter: ResponseFormatter,
        model_selector,
    ) -> None:
        self._input_normalizer = input_normalizer
        self._route_resolver = route_resolver
        self._dynamic_behavior_middleware = dynamic_behavior_middleware
        self._text_chat_use_case = text_chat_use_case
        self._weather_chat_use_case = weather_chat_use_case
        self._image_chat_use_case = image_chat_use_case
        self._response_formatter = response_formatter
        self._model_selector = model_selector

    def execute(self, request: AssistantChatRequest) -> AssistantResponse:
        normalized_request = self._input_normalizer.normalize(request)
        route = self._route_resolver.resolve(normalized_request)
        effective_request = self._dynamic_behavior_middleware.apply(
            normalized_request,
            route=route,
        )

        if route == "general_text":
            raw_result = self._text_chat_use_case.execute(effective_request)
        elif route == "weather_text":
            raw_result = self._weather_chat_use_case.execute(effective_request)
        elif route == "image_text":
            raw_result = self._image_chat_use_case.execute(effective_request)
        else:
            raise UnsupportedRouteError(f"Unsupported route: {route}")
        return self._response_formatter.format(
            raw_result=raw_result,
            model_name=self._model_selector.active_model_name(),
        )
