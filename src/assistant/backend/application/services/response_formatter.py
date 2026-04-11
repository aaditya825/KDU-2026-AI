from langchain_core.messages import AIMessage

from assistant.backend.contracts.responses import (
    AssistantResponse,
    GeneralTextResult,
    ImageTextResult,
    WeatherTextResult,
)


class ResponseFormatter:
    """Format raw chain output into the stable API response model."""

    def format(
        self,
        raw_result: GeneralTextResult | WeatherTextResult | ImageTextResult | AIMessage | str,
        model_name: str,
    ) -> AssistantResponse:
        if isinstance(raw_result, GeneralTextResult):
            answer = raw_result.answer
            route = "general_text"
            location = None
            temperature_c = None
            summary = None
            description = None
            objects = None
        elif isinstance(raw_result, WeatherTextResult):
            answer = (
                f"The weather in {raw_result.location} is "
                f"{raw_result.temperature_c} degrees C with {raw_result.summary.lower()}"
            )
            route = "weather_text"
            location = raw_result.location
            temperature_c = raw_result.temperature_c
            summary = raw_result.summary
            description = None
            objects = None
        elif isinstance(raw_result, ImageTextResult):
            answer = raw_result.answer
            route = "image_text"
            location = None
            temperature_c = None
            summary = raw_result.summary
            description = raw_result.description
            objects = raw_result.objects
        elif isinstance(raw_result, AIMessage):
            answer = raw_result.content if isinstance(raw_result.content, str) else str(raw_result.content)
            route = "general_text"
            location = None
            temperature_c = None
            summary = None
            description = None
            objects = None
        else:
            answer = str(raw_result)
            route = "general_text"
            location = None
            temperature_c = None
            summary = None
            description = None
            objects = None

        return AssistantResponse(
            route=route,
            answer=answer,
            model=model_name,
            location=location,
            temperature_c=temperature_c,
            summary=summary,
            description=description,
            objects=objects,
        )
