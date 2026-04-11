from assistant.backend.application.services.weather_service import WeatherSnapshot


class WeatherToolCaller:
    """Run the explicit model-driven weather tool-calling flow."""

    _tool_name = "get_current_weather"

    def __init__(self, prompt_factory, model_selector, weather_tool_provider) -> None:
        self._prompt_factory = prompt_factory
        self._model_selector = model_selector
        self._weather_tool_provider = weather_tool_provider

    def get_weather(
        self,
        *,
        message: str,
        resolved_location: str,
        user_name: str,
    ) -> WeatherSnapshot:
        weather_tool = self._weather_tool_provider.get_tool()
        prompt = self._prompt_factory.build_weather_tool_call_prompt()
        tool_calling_model = self._model_selector.select_tool_calling_model([weather_tool])
        messages = prompt.invoke(
            {
                "message": message,
                "resolved_location": resolved_location,
                "user_name": user_name,
            }
        ).to_messages()
        ai_message = tool_calling_model.invoke(messages)
        tool_call = self._select_weather_tool_call(ai_message.tool_calls)

        if tool_call is None:
            tool_result = weather_tool.invoke({"location": resolved_location})
        else:
            tool_result = weather_tool.invoke(tool_call.get("args", {}))

        return WeatherSnapshot(
            location=tool_result["location"],
            temperature_c=int(tool_result["temperature_c"]),
            condition=tool_result["condition"],
        )

    def _select_weather_tool_call(self, tool_calls: list[dict]) -> dict | None:
        for tool_call in tool_calls:
            if tool_call.get("name") == self._tool_name:
                return tool_call
        return None
