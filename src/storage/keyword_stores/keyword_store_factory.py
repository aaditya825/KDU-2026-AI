"""Factory for keyword stores."""

from __future__ import annotations

from src.core.interfaces import KeywordStore
from src.storage.keyword_stores.bm25_store import BM25KeywordStore


class KeywordStoreFactory:
    _registry: dict[str, type[KeywordStore]] = {
        "bm25": BM25KeywordStore,
    }

    @classmethod
    def register(cls, name: str, store_cls: type[KeywordStore]) -> None:
        cls._registry[name.lower()] = store_cls

    @classmethod
    def create(cls, name: str, **kwargs: object) -> KeywordStore:
        try:
            store_cls = cls._registry[name.lower()]
        except KeyError as exc:
            raise ValueError(f"Unsupported keyword store '{name}'.") from exc
        return store_cls(**kwargs)
