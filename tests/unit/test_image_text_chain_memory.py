from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from assistant.backend.application.services.message_history_store import MessageHistoryStore
from assistant.backend.application.services.multimodal_message_builder import (
    MultimodalMessageBuilder,
)
from assistant.backend.application.services.input_normalizer import (
    NormalizedAssistantRequest,
)
from assistant.backend.application.services.prompt_factory import PromptFactory
from assistant.backend.chains.image_text_chain import ImageTextChainBuilder


class StubModelSelector:
    def select_default_text_model(self, output_schema=None):
        return RunnableLambda(lambda messages: AIMessage(content="stubbed"))


def test_image_text_chain_uses_session_scoped_message_history() -> None:
    history_store = MessageHistoryStore()
    chain = ImageTextChainBuilder(
        prompt_factory=PromptFactory(),
        model_selector=StubModelSelector(),
        message_history_store=history_store,
    ).build()
    message_builder = MultimodalMessageBuilder()
    request = NormalizedAssistantRequest(
        message="Describe this image",
        session_id="session-1",
        user_id="user-1",
        image_bytes=b"img",
        image_mime_type="image/png",
    )

    first_input = message_builder.build_image_analysis_message(request, user_name="Alice")
    second_input = message_builder.build_image_analysis_message(request, user_name="Alice")

    chain.invoke(
        {"current_input": first_input},
        config={"configurable": {"session_id": "session-1"}},
    )
    chain.invoke(
        {"current_input": second_input},
        config={"configurable": {"session_id": "session-1"}},
    )

    history = history_store.get_session_history("session-1")

    assert len(history.messages) == 4
