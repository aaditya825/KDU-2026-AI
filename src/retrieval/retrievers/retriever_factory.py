"""Factory for retriever implementations."""

from __future__ import annotations

from src.core.interfaces import Retriever
from src.retrieval.retrievers.hybrid_retriever import HybridRetriever
from src.retrieval.retrievers.keyword_retriever import KeywordRetriever
from src.retrieval.retrievers.semantic_retriever import SemanticRetriever


class RetrieverFactory:
    _registry: dict[str, type[Retriever]] = {
        "semantic": SemanticRetriever,
        "keyword": KeywordRetriever,
        "hybrid": HybridRetriever,
    }

    @classmethod
    def register(cls, name: str, retriever_cls: type[Retriever]) -> None:
        cls._registry[name.lower()] = retriever_cls

    @classmethod
    def create(cls, name: str, **kwargs: object) -> Retriever:
        try:
            retriever_cls = cls._registry[name.lower()]
        except KeyError as exc:
            raise ValueError(f"Unsupported retriever '{name}'.") from exc
        return retriever_cls(**kwargs)

    @classmethod
    def create_default_hybrid(
        cls,
        *,
        semantic_retriever: Retriever,
        keyword_retriever: Retriever,
        fused_top_k: int = 10,
    ) -> Retriever:
        return cls.create(
            "hybrid",
            semantic_retriever=semantic_retriever,
            keyword_retriever=keyword_retriever,
            fused_top_k=fused_top_k,
        )
