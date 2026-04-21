from __future__ import annotations

import unittest

from tri_model_assistant.core.router import QueryRouter, Route


class QueryRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = QueryRouter()

    def test_routes_summarize_queries(self) -> None:
        decision = self.router.route("Summarize this document")
        self.assertEqual(decision.route, Route.SUMMARIZE)

    def test_routes_refine_short_queries(self) -> None:
        decision = self.router.route("Give me a short summary")
        self.assertEqual(decision.route, Route.REFINE_SHORT)

    def test_routes_refine_medium_queries(self) -> None:
        decision = self.router.route("Give me a medium summary")
        self.assertEqual(decision.route, Route.REFINE_MEDIUM)

    def test_routes_refine_long_queries(self) -> None:
        decision = self.router.route("Make it more detailed")
        self.assertEqual(decision.route, Route.REFINE_LONG)

    def test_routes_exit_queries(self) -> None:
        decision = self.router.route("exit")
        self.assertEqual(decision.route, Route.EXIT)

    def test_defaults_to_qa_for_regular_questions(self) -> None:
        decision = self.router.route("What are the key risks?")
        self.assertEqual(decision.route, Route.QA)

    def test_routes_broad_document_synthesis_queries_to_qa(self) -> None:
        decision = self.router.route("What are the main ideas?")
        self.assertEqual(decision.route, Route.QA)

    def test_prioritizes_short_refinement_when_query_has_conflicting_keywords(self) -> None:
        decision = self.router.route("Summarize briefly but make it detailed")
        self.assertEqual(decision.route, Route.REFINE_SHORT)


if __name__ == "__main__":
    unittest.main()
