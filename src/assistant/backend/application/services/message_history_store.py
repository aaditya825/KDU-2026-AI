from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory


class MessageHistoryStore:
    """Session-scoped in-memory chat history store for RunnableWithMessageHistory."""

    def __init__(self) -> None:
        self._sessions: dict[str, InMemoryChatMessageHistory] = {}

    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        if session_id not in self._sessions:
            self._sessions[session_id] = InMemoryChatMessageHistory()
        return self._sessions[session_id]
