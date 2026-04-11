from assistant.backend.application.services.prompt_factory import PromptFactory


def test_prompt_factory_normalizes_unknown_profile_values_to_safe_defaults() -> None:
    factory = PromptFactory()

    assert factory.normalize_communication_style("unexpected-style") == "neutral"
    assert factory.normalize_expertise_level("unexpected-level") == "general"
    assert factory.normalize_response_length("unexpected-length") == "medium"


def test_prompt_factory_weather_guardrails_are_strict() -> None:
    factory = PromptFactory()

    guardrails = factory.build_route_guardrails("weather_text")
    schema_alignment = factory.build_schema_alignment_instruction("weather_text")

    assert "Use only the supplied location, temperature_c, and condition fields." in guardrails
    assert "Do not mention forecasts, humidity, wind, causes" in guardrails
    assert "summary should be short and directly derived from condition" in schema_alignment


def test_prompt_factory_image_guardrails_limit_inference() -> None:
    factory = PromptFactory()

    guardrails = factory.build_route_guardrails("image_text")
    schema_alignment = factory.build_schema_alignment_instruction("image_text")

    assert "Describe only visible content." in guardrails
    assert "Do not identify people, brands, intent, or hidden context" in guardrails
    assert "objects must contain only concrete visible objects" in schema_alignment


def test_prompt_factory_general_text_guardrails_avoid_invented_context() -> None:
    factory = PromptFactory()

    behavior = factory.build_behavior_instruction("general_text")
    guardrails = factory.build_route_guardrails("general_text")

    assert "If something is uncertain, state uncertainty briefly." in behavior
    assert "Do not invent context not present in the request or history." in behavior
    assert "Do not make unsupported certainty claims" in guardrails


def test_prompt_factory_weather_tool_prompt_requires_tool_call() -> None:
    factory = PromptFactory()

    prompt = factory.build_weather_tool_call_prompt()
    rendered = prompt.invoke(
        {
            "message": "What's the weather in Delhi today?",
            "resolved_location": "Delhi",
            "user_name": "Aarav",
        }
    )
    rendered_messages = rendered.to_messages()

    assert "must call the get_current_weather tool exactly once" in rendered_messages[0].content
    assert "resolved_location: Delhi" in rendered_messages[1].content
