from functools import lru_cache

from assistant.backend.application.services.dynamic_behavior_middleware import (
    DynamicBehaviorMiddleware,
)
from assistant.backend.application.services.input_normalizer import InputNormalizer
from assistant.backend.application.services.message_history_store import MessageHistoryStore
from assistant.backend.application.services.multimodal_message_builder import (
    MultimodalMessageBuilder,
)
from assistant.backend.application.services.prompt_factory import PromptFactory
from assistant.backend.application.services.response_formatter import ResponseFormatter
from assistant.backend.application.services.route_resolver import RouteResolver
from assistant.backend.application.services.user_profile_store import UserProfileStore
from assistant.backend.application.services.weather_service import WeatherService
from assistant.backend.application.services.weather_tool_caller import WeatherToolCaller
from assistant.backend.application.services.weather_tool_provider import (
    WeatherToolProvider,
)
from assistant.backend.application.use_cases.image_chat import ImageChatUseCase
from assistant.backend.application.use_cases.text_chat import TextChatUseCase
from assistant.backend.application.use_cases.weather_chat import WeatherChatUseCase
from assistant.backend.chains.general_text_chain import GeneralTextChainBuilder
from assistant.backend.chains.image_text_chain import ImageTextChainBuilder
from assistant.backend.chains.weather_text_chain import WeatherTextChainBuilder
from assistant.backend.infrastructure.llm.model_selector import ModelSelector
from assistant.backend.orchestrator.assistant_orchestrator import AssistantOrchestrator
from assistant.backend.shared.settings import get_settings


@lru_cache(maxsize=1)
def get_profile_store() -> UserProfileStore:
    return UserProfileStore()


@lru_cache(maxsize=1)
def get_orchestrator() -> AssistantOrchestrator:
    settings = get_settings()
    prompt_factory = PromptFactory()
    message_history_store = MessageHistoryStore()
    profile_store = get_profile_store()
    model_selector = ModelSelector(settings=settings)
    model_selector.validate_configuration()
    chain_builder = GeneralTextChainBuilder(
        prompt_factory=prompt_factory,
        model_selector=model_selector,
        message_history_store=message_history_store,
    )
    text_chat_use_case = TextChatUseCase(
        profile_store=profile_store,
        prompt_factory=prompt_factory,
        chain_builder=chain_builder,
    )
    weather_chain_builder = WeatherTextChainBuilder(
        prompt_factory=prompt_factory,
        model_selector=model_selector,
        message_history_store=message_history_store,
    )
    weather_chat_use_case = WeatherChatUseCase(
        profile_store=profile_store,
        weather_tool_caller=WeatherToolCaller(
            prompt_factory=prompt_factory,
            model_selector=model_selector,
            weather_tool_provider=WeatherToolProvider(
                WeatherService(
                    geocoding_url=settings.weather_geocoding_url,
                    forecast_url=settings.weather_forecast_url,
                    timeout_seconds=settings.weather_timeout_seconds,
                )
            ),
        ),
        prompt_factory=prompt_factory,
        chain_builder=weather_chain_builder,
    )
    image_chain_builder = ImageTextChainBuilder(
        prompt_factory=prompt_factory,
        model_selector=model_selector,
        message_history_store=message_history_store,
    )
    image_chat_use_case = ImageChatUseCase(
        profile_store=profile_store,
        prompt_factory=prompt_factory,
        message_builder=MultimodalMessageBuilder(),
        chain_builder=image_chain_builder,
    )

    return AssistantOrchestrator(
        input_normalizer=InputNormalizer(
            max_image_bytes=settings.assistant_max_image_bytes,
        ),
        route_resolver=RouteResolver(),
        dynamic_behavior_middleware=DynamicBehaviorMiddleware(),
        text_chat_use_case=text_chat_use_case,
        weather_chat_use_case=weather_chat_use_case,
        image_chat_use_case=image_chat_use_case,
        response_formatter=ResponseFormatter(),
        model_selector=model_selector,
    )
