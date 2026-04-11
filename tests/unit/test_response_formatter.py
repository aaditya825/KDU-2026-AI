from assistant.backend.application.services.response_formatter import ResponseFormatter
from assistant.backend.contracts.responses import (
    GeneralTextResult,
    ImageTextResult,
    WeatherTextResult,
)


def test_response_formatter_handles_structured_result() -> None:
    formatter = ResponseFormatter()

    response = formatter.format(
        raw_result=GeneralTextResult(answer="Structured answer"),
        model_name="gemini-2.5-flash",
    )

    assert response.answer == "Structured answer"
    assert response.model == "gemini-2.5-flash"


def test_response_formatter_handles_weather_result() -> None:
    formatter = ResponseFormatter()

    response = formatter.format(
        raw_result=WeatherTextResult(
            answer="It is warm in Mumbai.",
            location="Mumbai",
            temperature_c=31,
            summary="Warm and humid.",
        ),
        model_name="gemini-2.5-flash",
    )

    assert response.route == "weather_text"
    assert response.location == "Mumbai"
    assert response.temperature_c == 31
    assert response.summary == "Warm and humid."


def test_response_formatter_handles_image_result() -> None:
    formatter = ResponseFormatter()

    response = formatter.format(
        raw_result=ImageTextResult(
            answer="A laptop sits on a desk.",
            description="A laptop on a desk beside a coffee mug.",
            objects=["laptop", "desk", "coffee mug"],
            summary="Indoor workspace scene.",
        ),
        model_name="gemini-2.5-flash",
    )

    assert response.route == "image_text"
    assert response.description == "A laptop on a desk beside a coffee mug."
    assert response.objects == ["laptop", "desk", "coffee mug"]
    assert response.summary == "Indoor workspace scene."
