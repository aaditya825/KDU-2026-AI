from langchain_core.messages import HumanMessage

from assistant.backend.application.services.input_normalizer import (
    NormalizedAssistantRequest,
)
from assistant.backend.application.services.prompt_factory import PromptFactory
from assistant.backend.application.use_cases.image_chat import ImageChatUseCase


class StubImageChain:
    def __init__(self) -> None:
        self.last_payload = None
        self.last_config = None

    def invoke(self, payload, config=None):
        self.last_payload = payload
        self.last_config = config
        return {"answer": "image stub"}


class StubImageChainBuilder:
    def __init__(self) -> None:
        self.chain = StubImageChain()

    def build(self):
        return self.chain


class StubProfileStore:
    class Profile:
        name = "Alice"

    def get_profile(self, _user_id):
        return self.Profile()


class StubMessageBuilder:
    def build_image_analysis_message(self, request, *, user_name: str):
        return HumanMessage(content=f"{user_name}: {request.message}")


def test_image_use_case_passes_multimodal_message_and_session_id() -> None:
    chain_builder = StubImageChainBuilder()
    use_case = ImageChatUseCase(
        profile_store=StubProfileStore(),
        prompt_factory=PromptFactory(),
        message_builder=StubMessageBuilder(),
        chain_builder=chain_builder,
    )

    use_case.execute(
        NormalizedAssistantRequest(
            message="Describe this image",
            session_id="session-123",
            user_id="user-1",
            communication_style="technical",
            expertise_level="expert",
            preferred_response_length="detailed",
            image_bytes=b"img",
            image_mime_type="image/png",
        )
    )

    current_input = chain_builder.chain.last_payload["current_input"]
    assert isinstance(current_input, HumanMessage)
    assert chain_builder.chain.last_payload["user_name"] == "Alice"
    assert chain_builder.chain.last_payload["communication_style"] == "technical"
    assert chain_builder.chain.last_payload["expertise_level"] == "expert"
    assert chain_builder.chain.last_payload["preferred_response_length"] == "detailed"
    assert chain_builder.chain.last_config == {"configurable": {"session_id": "session-123"}}
