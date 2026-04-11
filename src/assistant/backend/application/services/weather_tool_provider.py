from langchain_core.tools import tool

from assistant.backend.application.services.weather_service import WeatherService


class WeatherToolProvider:
    """Expose weather lookup as a LangChain tool."""

    def __init__(self, weather_service: WeatherService) -> None:
        self._weather_service = weather_service
        self._tool = self._build_tool()

    def get_tool(self):
        return self._tool

    def _build_tool(self):
        weather_service = self._weather_service

        @tool("get_current_weather")
        def get_current_weather(location: str) -> dict:
            """Get the current weather for a location."""

            snapshot = weather_service.get_weather(location)
            return {
                "location": snapshot.location,
                "temperature_c": snapshot.temperature_c,
                "condition": snapshot.condition,
            }

        return get_current_weather
