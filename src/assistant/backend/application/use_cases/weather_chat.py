import re

from assistant.backend.application.services.input_normalizer import (
    NormalizedAssistantRequest,
)


class WeatherChatUseCase:
    """Execute the weather capability with profile-based location inference."""

    _location_pattern = re.compile(
        r"\b(?:in|for|at)\s+([A-Za-z][A-Za-z\s-]{1,50})",
        flags=re.IGNORECASE,
    )
    _trailing_phrase_pattern = re.compile(
        r"\b(?:right now|currently|today|tonight|tomorrow|now|please|this morning|this afternoon|this evening)\b[\s?!.,]*$",
        flags=re.IGNORECASE,
    )

    def __init__(self, profile_store, weather_tool_caller, prompt_factory, chain_builder) -> None:
        self._profile_store = profile_store
        self._weather_tool_caller = weather_tool_caller
        self._prompt_factory = prompt_factory
        self._chain_builder = chain_builder

    def execute(self, request: NormalizedAssistantRequest):
        profile = self._profile_store.get_profile(request.user_id)
        location = self._extract_location_from_message(request.message) or profile.location
        weather = self._weather_tool_caller.get_weather(
            message=request.message,
            resolved_location=location,
            user_name=profile.name,
        )

        chain = self._chain_builder.build()
        return chain.invoke(
            {
                "message": request.message,
                "user_name": profile.name,
                "location": weather.location,
                "temperature_c": weather.temperature_c,
                "condition": weather.condition,
                "communication_style_instruction": self._prompt_factory.build_communication_style_instruction(
                    request.communication_style
                ),
                "expertise_instruction": self._prompt_factory.build_expertise_instruction(
                    request.expertise_level
                ),
                "response_length_instruction": self._prompt_factory.build_response_length_instruction(
                    request.preferred_response_length
                ),
            },
            config={"configurable": {"session_id": request.session_id}},
        )

    def _extract_location_from_message(self, message: str) -> str | None:
        match = self._location_pattern.search(message)
        if not match:
            return None

        location = match.group(1).strip(" ?!.,")
        cleaned = self._strip_trailing_phrases(location)
        return cleaned or None

    def _strip_trailing_phrases(self, location: str) -> str:
        cleaned = location.strip()
        while cleaned:
            updated = self._trailing_phrase_pattern.sub("", cleaned).strip(" ?!.,")
            if updated == cleaned:
                break
            cleaned = updated
        return cleaned
