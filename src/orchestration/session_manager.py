"""Session state helpers."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.models import Document, Query, Response


@dataclass(slots=True)
class SessionState:
    active_document_ids: list[str] = field(default_factory=list)
    active_sources: list[str] = field(default_factory=list)
    queries: list[Query] = field(default_factory=list)
    responses: list[Response] = field(default_factory=list)
    last_error: str | None = None
    settings_overrides: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class SessionManager:
    sessions: dict[str, SessionState] = field(default_factory=dict)

    def get_or_create(self, session_id: str) -> SessionState:
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionState()
        return self.sessions[session_id]

    def add_document(self, session_id: str, document: Document) -> None:
        state = self.get_or_create(session_id)
        if document.document_id not in state.active_document_ids:
            state.active_document_ids.append(document.document_id)
        reference = document.reference_label()
        if reference not in state.active_sources:
            state.active_sources.append(reference)
        state.last_error = None

    def record_interaction(self, session_id: str, query: Query, response: Response) -> None:
        state = self.get_or_create(session_id)
        state.queries.append(query)
        state.responses.append(response)
        state.last_error = response.metadata.get("user_error") if isinstance(response.metadata, dict) else None

    def set_error(self, session_id: str, message: str) -> None:
        self.get_or_create(session_id).last_error = message

    def clear_error(self, session_id: str) -> None:
        self.get_or_create(session_id).last_error = None

    def set_settings_overrides(self, session_id: str, overrides: dict[str, object]) -> None:
        self.get_or_create(session_id).settings_overrides = dict(overrides)

    def build_filters(self, session_id: str, extra_filters: dict[str, object] | None = None) -> dict[str, object]:
        state = self.get_or_create(session_id)
        filters: dict[str, object] = {}
        if state.active_document_ids:
            filters["document_id"] = list(state.active_document_ids)
        if extra_filters:
            filters.update(extra_filters)
        return filters
