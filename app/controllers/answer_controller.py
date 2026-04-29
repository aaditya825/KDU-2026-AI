"""
app/controllers/answer_controller.py
------------------------------------
Thin controller wrapper for grounded Q&A.
"""

from __future__ import annotations

from app.controllers.search_controller import SearchController
from app.models.domain import AnswerResult


class AnswerController:
    """Public AnswerController interface expected by the implementation plan."""

    def __init__(self, search_controller: SearchController | None = None) -> None:
        self._search_controller = search_controller or SearchController()

    def answer(self, file_id: str, query: str, top_k: int = 5) -> AnswerResult:
        return self._search_controller.answer(file_id=file_id, question=query, top_k=top_k)
