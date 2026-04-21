from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Route(str, Enum):
    SUMMARIZE = "SUMMARIZE"
    REFINE_SHORT = "REFINE_SHORT"
    REFINE_MEDIUM = "REFINE_MEDIUM"
    REFINE_LONG = "REFINE_LONG"
    QA = "QA"
    EXIT = "EXIT"


@dataclass(slots=True)
class RouteDecision:
    route: Route
    reason: str


class QueryRouter:
    _EXIT_QUERIES = {"exit", "quit", "q", "bye"}
    _SHORT_KEYWORDS = ("short", "brief", "concise", "shrink", "shorter")
    _MEDIUM_KEYWORDS = ("medium", "balanced", "standard length", "normal length")
    _LONG_KEYWORDS = ("long", "longer", "detailed", "detail", "expand", "more detail", "elaborate")
    _SUMMARIZE_PHRASES = (
        "summarize",
        "summary",
        "overview",
        "give me the gist",
        "what is this document about",
        "what is this text about",
    )

    def route(self, query: str) -> RouteDecision:
        normalized = " ".join(query.strip().lower().split())
        if not normalized:
            return RouteDecision(route=Route.QA, reason="Empty queries default to the QA path.")

        if normalized in self._EXIT_QUERIES:
            return RouteDecision(route=Route.EXIT, reason="Matched an exit command.")

        if self._contains_any(normalized, self._SHORT_KEYWORDS):
            return RouteDecision(route=Route.REFINE_SHORT, reason="Detected a short-summary refinement request.")

        if self._contains_any(normalized, self._MEDIUM_KEYWORDS):
            return RouteDecision(route=Route.REFINE_MEDIUM, reason="Detected a medium-summary refinement request.")

        if self._contains_any(normalized, self._LONG_KEYWORDS):
            return RouteDecision(route=Route.REFINE_LONG, reason="Detected a long-summary refinement request.")

        if self._contains_any(normalized, self._SUMMARIZE_PHRASES):
            return RouteDecision(route=Route.SUMMARIZE, reason="Detected a summarization request.")

        return RouteDecision(route=Route.QA, reason="No summary keywords matched, so the query is treated as QA.")

    @staticmethod
    def _contains_any(query: str, keywords: tuple[str, ...]) -> bool:
        return any(keyword in query for keyword in keywords)
