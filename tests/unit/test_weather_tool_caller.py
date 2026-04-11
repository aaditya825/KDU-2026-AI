from langchain_core.messages import AIMessage

from assistant.backend.application.services.prompt_factory import PromptFactory
from assistant.backend.application.services.weather_service import WeatherSnapshot
from assistant.backend.application.services.weather_tool_caller import WeatherToolCaller


class StubToolCallingModel:
    def __init__(self) -> None:
        self.last_messages = None

    def invoke(self, messages):
        self.last_messages = messages
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "get_current_weather",
                    "args": {"location": "Delhi"},
                    "id": "tool-call-1",
                    "type": "tool_call",
                }
            ],
        )


class StubModelSelector:
    def __init__(self) -> None:
        self.model = StubToolCallingModel()

    def select_tool_calling_model(self, tools):
        self.last_tools = tools
        return self.model


class StubWeatherTool:
    def __init__(self) -> None:
        self.last_args = None

    def invoke(self, args):
        self.last_args = args
        return {
            "location": "Delhi",
            "temperature_c": 34,
            "condition": "Hot and dry",
        }


class StubWeatherToolProvider:
    def __init__(self) -> None:
        self.tool = StubWeatherTool()

    def get_tool(self):
        return self.tool


def test_weather_tool_caller_executes_tool_call_and_returns_snapshot() -> None:
    model_selector = StubModelSelector()
    tool_provider = StubWeatherToolProvider()
    caller = WeatherToolCaller(
        prompt_factory=PromptFactory(),
        model_selector=model_selector,
        weather_tool_provider=tool_provider,
    )

    result = caller.get_weather(
        message="What is the weather in Delhi today?",
        resolved_location="Delhi",
        user_name="Aarav",
    )

    assert isinstance(result, WeatherSnapshot)
    assert result.location == "Delhi"
    assert result.temperature_c == 34
    assert result.condition == "Hot and dry"
    assert tool_provider.tool.last_args == {"location": "Delhi"}


def test_weather_tool_caller_falls_back_to_resolved_location_when_model_skips_tool_call() -> None:
    class NoToolCallModel:
        def invoke(self, messages):
            return AIMessage(content="", tool_calls=[])

    class NoToolCallSelector:
        def select_tool_calling_model(self, tools):
            return NoToolCallModel()

    tool_provider = StubWeatherToolProvider()
    caller = WeatherToolCaller(
        prompt_factory=PromptFactory(),
        model_selector=NoToolCallSelector(),
        weather_tool_provider=tool_provider,
    )

    result = caller.get_weather(
        message="Weather please",
        resolved_location="Delhi",
        user_name="Aarav",
    )

    assert result.location == "Delhi"
    assert tool_provider.tool.last_args == {"location": "Delhi"}
