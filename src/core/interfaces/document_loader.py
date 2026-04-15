"""Interface for document loaders."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.models import Document


class DocumentLoader(ABC):
    """Loads a source into the canonical Document contract."""

    supported_source_types: tuple[str, ...] = ()

    @abstractmethod
    def load(self, source: str) -> Document:
        """Load a source location or identifier into a document."""

    def can_handle(self, source_type: str) -> bool:
        return source_type.lower() in self.supported_source_types
