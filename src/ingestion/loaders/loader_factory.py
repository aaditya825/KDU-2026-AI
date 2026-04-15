"""Factory for document loaders."""

from __future__ import annotations

from collections.abc import Mapping

from src.core.interfaces import DocumentLoader
from src.ingestion.loaders.pdf_loader import PDFLoader
from src.ingestion.loaders.text_loader import TextLoader
from src.ingestion.loaders.url_loader import URLLoader


class LoaderFactory:
    """Thin registry for document loader implementations."""

    _registry: dict[str, type[DocumentLoader]] = {
        "pdf": PDFLoader,
        "url": URLLoader,
        "blog": URLLoader,
        "text": TextLoader,
    }

    @classmethod
    def register(cls, name: str, loader_cls: type[DocumentLoader]) -> None:
        cls._registry[name.lower()] = loader_cls

    @classmethod
    def create(cls, name: str, **kwargs: object) -> DocumentLoader:
        try:
            loader_cls = cls._registry[name.lower()]
        except KeyError as exc:
            raise ValueError(f"Unsupported loader '{name}'.") from exc
        return loader_cls(**kwargs)

    @classmethod
    def create_mapping(cls, config: Mapping[str, dict[str, object]] | None = None) -> dict[str, DocumentLoader]:
        mapping: dict[str, DocumentLoader] = {}
        for name, loader_cls in cls._registry.items():
            mapping[name] = loader_cls(**(config or {}).get(name, {}))
        return mapping

    @classmethod
    def detect_source_type(cls, source: str) -> str:
        lowered = source.lower().strip()
        if lowered.startswith("http://") or lowered.startswith("https://"):
            return "url"
        if lowered.endswith(".pdf"):
            return "pdf"
        return "text"
