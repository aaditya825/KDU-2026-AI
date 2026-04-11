from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from assistant.backend.application.services.message_history_store import MessageHistoryStore
from assistant.backend.application.services.prompt_factory import PromptFactory
from assistant.backend.chains.general_text_chain import GeneralTextChainBuilder


class StubModelSelector:
    def select_default_text_model(self, output_schema=None):
        return RunnableLambda(lambda prompt_value: AIMessage(content="stubbed"))


def test_general_text_chain_uses_session_scoped_message_history() -> None:
    history_store = MessageHistoryStore()
    chain = GeneralTextChainBuilder(
        prompt_factory=PromptFactory(),
        model_selector=StubModelSelector(),
        message_history_store=history_store,
    ).build()

    chain.invoke(
        {"message": "Hello"},
        config={"configurable": {"session_id": "session-1"}},
    )
    chain.invoke(
        {"message": "What did I just say?"},
        config={"configurable": {"session_id": "session-1"}},
    )

    history = history_store.get_session_history("session-1")

    assert len(history.messages) == 4
    assert history.messages[0].content == "Hello"
    assert history.messages[1].content == "stubbed"
    assert history.messages[2].content == "What did I just say?"
    assert history.messages[3].content == "stubbed"
