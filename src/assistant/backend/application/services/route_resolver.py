from assistant.backend.application.services.input_normalizer import (
    NormalizedAssistantRequest,
)


class RouteResolver:
    """Resolve which capability should handle the normalized request.

    The active MVP supports `general_text` and `weather_text`.
    """

    def resolve(self, request: NormalizedAssistantRequest) -> str:
        if request.has_image:
            return "image_text"
        message = request.message.lower()
        weather_keywords = ("weather", "temperature", "forecast", "rain", "hot", "cold")
        if any(keyword in message for keyword in weather_keywords):
            return "weather_text"
        return "general_text"
