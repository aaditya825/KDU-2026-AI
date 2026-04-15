"""Lightweight in-memory cache helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CacheManager:
    cache: dict[str, Any] = field(default_factory=dict)
    _session_keys: dict[str, set[str]] = field(default_factory=dict)

    def get(self, key: str) -> Any | None:
        return self.cache.get(key)

    def set(self, key: str, value: Any, *, session_id: str | None = None) -> None:
        self.cache[key] = value
        if session_id:
            self._session_keys.setdefault(session_id, set()).add(key)

    def clear(self) -> None:
        self.cache.clear()
        self._session_keys.clear()

    def delete(self, key: str) -> None:
        self.cache.pop(key, None)
        empty_sessions: list[str] = []
        for session_id, keys in self._session_keys.items():
            keys.discard(key)
            if not keys:
                empty_sessions.append(session_id)
        for session_id in empty_sessions:
            self._session_keys.pop(session_id, None)

    def delete_session(self, session_id: str) -> None:
        keys = list(self._session_keys.pop(session_id, set()))
        for key in keys:
            self.cache.pop(key, None)

    def build_query_key(
        self,
        *,
        session_id: str,
        question: str,
        document_ids: list[str],
        filters: dict[str, Any],
        settings_overrides: dict[str, Any] | None = None,
    ) -> str:
        payload = {
            "session_id": session_id,
            "question": question,
            "document_ids": sorted(document_ids),
            "filters": filters,
            "settings_overrides": settings_overrides or {},
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
