from assistant.backend.application.services.input_normalizer import NormalizedAssistantRequest
from assistant.backend.application.services.prompt_factory import PromptFactory
from assistant.backend.application.services.user_profile_store import UserProfileStore
from assistant.backend.application.services.weather_service import WeatherSnapshot
from assistant.backend.application.use_cases.weather_chat import WeatherChatUseCase


class StubWeatherChain:
    def __init__(self) -> None:
        self.last_payload = None
        self.last_config = None

    def invoke(self, payload, config=None):
        self.last_payload = payload
        self.last_config = config
        return payload


class StubWeatherChainBuilder:
    def __init__(self) -> None:
        self.chain = StubWeatherChain()

    def build(self):
        return self.chain


class StubWeatherToolCaller:
    def __init__(self) -> None:
        self.last_call = None
        self._data = {
            "San Francisco": WeatherSnapshot("San Francisco", 16, "Foggy with mild sun"),
            "Delhi": WeatherSnapshot("Delhi", 34, "Hot and dry"),
            "New York": WeatherSnapshot("New York", 22, "Light rain"),
        }

    def get_weather(self, *, message: str, resolved_location: str, user_name: str) -> WeatherSnapshot:
        self.last_call = {
            "message": message,
            "resolved_location": resolved_location,
            "user_name": user_name,
        }
        return self._data[resolved_location]


def test_weather_use_case_uses_profile_location_when_message_has_no_location() -> None:
    chain_builder = StubWeatherChainBuilder()
    tool_caller = StubWeatherToolCaller()
    use_case = WeatherChatUseCase(
        profile_store=UserProfileStore(),
        weather_tool_caller=tool_caller,
        prompt_factory=PromptFactory(),
        chain_builder=chain_builder,
    )

    result = use_case.execute(
        NormalizedAssistantRequest(
            message="What's the weather like today?",
            session_id="session-1",
            user_id="weather-demo",
            communication_style="friendly",
            expertise_level="expert",
            preferred_response_length="medium",
        )
    )

    assert tool_caller.last_call == {
        "message": "What's the weather like today?",
        "resolved_location": "San Francisco",
        "user_name": "Isha",
    }
    assert result["location"] == "San Francisco"
    assert result["temperature_c"] == 16
    assert result["communication_style_instruction"] == "Use a friendly, approachable tone."
    assert result["expertise_instruction"] == (
        "Assume the user is expert and include useful detail without oversimplifying."
    )
    assert result["response_length_instruction"] == "Keep the response moderately concise."
    assert chain_builder.chain.last_config == {"configurable": {"session_id": "session-1"}}


def test_weather_use_case_prefers_explicit_location_over_profile_location() -> None:
    chain_builder = StubWeatherChainBuilder()
    tool_caller = StubWeatherToolCaller()
    use_case = WeatherChatUseCase(
        profile_store=UserProfileStore(),
        weather_tool_caller=tool_caller,
        prompt_factory=PromptFactory(),
        chain_builder=chain_builder,
    )

    result = use_case.execute(
        NormalizedAssistantRequest(
            message="What is the weather in Delhi today?",
            session_id="session-1",
            user_id="weather-demo",
            communication_style="friendly",
            expertise_level="general",
            preferred_response_length="short",
        )
    )

    assert tool_caller.last_call["resolved_location"] == "Delhi"
    assert result["location"] == "Delhi"
    assert result["temperature_c"] == 34
    assert result["communication_style_instruction"] == "Use a friendly, approachable tone."
    assert chain_builder.chain.last_config == {"configurable": {"session_id": "session-1"}}


def test_weather_use_case_handles_trailing_time_words_in_location_prompt() -> None:
    chain_builder = StubWeatherChainBuilder()
    tool_caller = StubWeatherToolCaller()
    use_case = WeatherChatUseCase(
        profile_store=UserProfileStore(),
        weather_tool_caller=tool_caller,
        prompt_factory=PromptFactory(),
        chain_builder=chain_builder,
    )

    result = use_case.execute(
        NormalizedAssistantRequest(
            message="Will it rain in New York right now?",
            session_id="session-1",
            user_id="weather-demo",
            communication_style="neutral",
            expertise_level="general",
            preferred_response_length="short",
        )
    )

    assert tool_caller.last_call["resolved_location"] == "New York"
    assert result["location"] == "New York"
    assert result["temperature_c"] == 22
    assert result["communication_style_instruction"] == "Use a neutral, direct tone."
    assert result["expertise_instruction"] == (
        "Assume the user has general familiarity and keep explanations balanced."
    )
    assert result["response_length_instruction"] == "Keep the response brief."


def test_weather_location_extractor_returns_none_without_explicit_city() -> None:
    use_case = WeatherChatUseCase(
        profile_store=UserProfileStore(),
        weather_tool_caller=StubWeatherToolCaller(),
        prompt_factory=PromptFactory(),
        chain_builder=StubWeatherChainBuilder(),
    )

    extracted = use_case._extract_location_from_message("What is the weather like today?")

    assert extracted is None
