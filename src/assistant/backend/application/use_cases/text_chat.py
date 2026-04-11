from assistant.backend.application.services.input_normalizer import (
    NormalizedAssistantRequest,
)


class TextChatUseCase:
    """Execute the active text-only assistant capability."""

    def __init__(self, profile_store, prompt_factory, chain_builder) -> None:
        self._profile_store = profile_store
        self._prompt_factory = prompt_factory
        self._chain_builder = chain_builder

    def execute(self, request: NormalizedAssistantRequest):
        profile = self._profile_store.get_profile(request.user_id)
        chain = self._chain_builder.build()
        return chain.invoke(
            {
                "message": request.message,
                "user_name": profile.name,
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
