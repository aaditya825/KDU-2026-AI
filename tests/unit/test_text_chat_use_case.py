from assistant.backend.application.services.input_normalizer import NormalizedAssistantRequest
from assistant.backend.application.services.prompt_factory import PromptFactory
from assistant.backend.application.use_cases.text_chat import TextChatUseCase


class StubTextChain:
    def __init__(self) -> None:
        self.last_payload = None
        self.last_config = None

    def invoke(self, payload, config=None):
        self.last_payload = payload
        self.last_config = config
        return {"answer": "stubbed"}


class StubTextChainBuilder:
    def __init__(self) -> None:
        self.chain = StubTextChain()

    def build(self):
        return self.chain


class StubProfileStore:
    class Profile:
        name = "Aarav"

    def get_profile(self, _user_id):
        return self.Profile()


def test_text_chat_use_case_passes_session_id_to_chain_config() -> None:
    chain_builder = StubTextChainBuilder()
    use_case = TextChatUseCase(
        profile_store=StubProfileStore(),
        prompt_factory=PromptFactory(),
        chain_builder=chain_builder,
    )

    use_case.execute(
        NormalizedAssistantRequest(
            message="hello",
            session_id="session-123",
            user_id="user-1",
            communication_style="friendly",
            expertise_level="expert",
            preferred_response_length="short",
        )
    )

    assert chain_builder.chain.last_payload == {
        "message": "hello",
        "user_name": "Aarav",
        "communication_style_instruction": "Use a friendly, approachable tone.",
        "expertise_instruction": "Assume the user is expert and include useful detail without oversimplifying.",
        "response_length_instruction": "Keep the response brief.",
    }
    assert chain_builder.chain.last_config == {"configurable": {"session_id": "session-123"}}
