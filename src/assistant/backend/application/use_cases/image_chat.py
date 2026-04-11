from assistant.backend.application.services.input_normalizer import (
    NormalizedAssistantRequest,
)


class ImageChatUseCase:
    """Execute the image-analysis capability for multimodal requests."""

    def __init__(self, profile_store, prompt_factory, message_builder, chain_builder) -> None:
        self._profile_store = profile_store
        self._prompt_factory = prompt_factory
        self._message_builder = message_builder
        self._chain_builder = chain_builder

    def execute(self, request: NormalizedAssistantRequest):
        profile = self._profile_store.get_profile(request.user_id)
        current_input = self._message_builder.build_image_analysis_message(
            request,
            user_name=profile.name,
        )
        chain = self._chain_builder.build()
        return chain.invoke(
            {
                "current_input": current_input,
                "user_name": profile.name,
                "communication_style": request.communication_style,
                "expertise_level": request.expertise_level,
                "preferred_response_length": request.preferred_response_length,
            },
            config={"configurable": {"session_id": request.session_id}},
        )
