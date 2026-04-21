from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from tri_model_assistant.core.config import SummaryLength
from tri_model_assistant.core.router import QueryRouter, Route
from tri_model_assistant.core.state import AssistantState
from tri_model_assistant.models.pipeline import TriModelModelGateway
from tri_model_assistant.models.qa import HuggingFaceQAClient
from tri_model_assistant.processing.text_processing import (
    coerce_summary_to_word_bounds,
    extractive_summary_from_source,
    refinement_word_bounds,
    word_count,
)


class WorkflowState(TypedDict, total=False):
    assistant_state: AssistantState
    query: str
    route: Route
    route_reason: str
    response: str
    context_source: str
    model_used: str


@dataclass(slots=True)
class QueryOutcome:
    route: Route
    route_reason: str
    response: str
    context_source: str | None = None
    model_used: str | None = None


class QueryRoutedAssistant:
    def __init__(
        self,
        assistant_state: AssistantState,
        router: QueryRouter,
        model_gateway: TriModelModelGateway,
        qa_client: HuggingFaceQAClient,
    ) -> None:
        self._assistant_state = assistant_state
        self._router = router
        self._model_gateway = model_gateway
        self._qa_client = qa_client
        self._graph = self._build_graph()

    def handle_query(self, query: str) -> QueryOutcome:
        result = self._graph.invoke({"assistant_state": self._assistant_state, "query": query})
        self._assistant_state = result["assistant_state"]
        self._assistant_state.last_route = result["route"]
        self._assistant_state.last_response = result["response"]

        return QueryOutcome(
            route=result["route"],
            route_reason=result["route_reason"],
            response=result["response"],
            context_source=result.get("context_source"),
            model_used=result.get("model_used"),
        )

    @property
    def state(self) -> AssistantState:
        return self._assistant_state

    def _build_graph(self):
        graph = StateGraph(WorkflowState)
        graph.add_node("route", self._route_node)
        graph.add_node("summarize", self._summarize_node)
        graph.add_node("refine_short", self._refine_short_node)
        graph.add_node("refine_medium", self._refine_medium_node)
        graph.add_node("refine_long", self._refine_long_node)
        graph.add_node("qa", self._qa_node)
        graph.add_node("exit", self._exit_node)

        graph.add_edge(START, "route")
        graph.add_conditional_edges("route", self._select_next_node)
        graph.add_edge("summarize", END)
        graph.add_edge("refine_short", END)
        graph.add_edge("refine_medium", END)
        graph.add_edge("refine_long", END)
        graph.add_edge("qa", END)
        graph.add_edge("exit", END)
        return graph.compile()

    def _route_node(self, state: WorkflowState) -> WorkflowState:
        decision = self._router.route(state["query"])
        return {
            "assistant_state": state["assistant_state"],
            "query": state["query"],
            "route": decision.route,
            "route_reason": decision.reason,
        }

    @staticmethod
    def _select_next_node(state: WorkflowState) -> str:
        mapping = {
            Route.SUMMARIZE: "summarize",
            Route.REFINE_SHORT: "refine_short",
            Route.REFINE_MEDIUM: "refine_medium",
            Route.REFINE_LONG: "refine_long",
            Route.QA: "qa",
            Route.EXIT: "exit",
        }
        return mapping[state["route"]]

    def _summarize_node(self, state: WorkflowState) -> WorkflowState:
        assistant_state = state["assistant_state"]
        if assistant_state.draft_summary is None:
            artifacts = self._model_gateway.generate_draft_summary(assistant_state.original_text)
            assistant_state.store_draft_summary(artifacts)

        response = assistant_state.draft_summary or ""
        context_source = "draft_summary"

        return {
            **state,
            "assistant_state": assistant_state,
            "response": response,
            "context_source": context_source,
            "model_used": f"Summarization ({self._model_gateway.summarizer_model_name})",
        }

    def _refine_short_node(self, state: WorkflowState) -> WorkflowState:
        return self._refine_node(state, SummaryLength.SHORT)

    def _refine_medium_node(self, state: WorkflowState) -> WorkflowState:
        return self._refine_node(state, SummaryLength.MEDIUM)

    def _refine_long_node(self, state: WorkflowState) -> WorkflowState:
        return self._refine_node(state, SummaryLength.LONG)

    def _refine_node(self, state: WorkflowState, summary_length: SummaryLength) -> WorkflowState:
        assistant_state = state["assistant_state"]
        if assistant_state.draft_summary is None:
            artifacts = self._model_gateway.generate_draft_summary(assistant_state.original_text)
            assistant_state.store_draft_summary(artifacts)

        cached_summary = assistant_state.get_refined_summary(summary_length)
        if cached_summary is None:
            cached_summary = self._model_gateway.refine_summary(assistant_state.draft_summary or "", summary_length)
            assistant_state.store_refined_summary(summary_length, cached_summary)
        else:
            assistant_state.current_summary = cached_summary
            assistant_state.current_summary_length = summary_length

        cached_summary = self._enforce_refinement_order(
            assistant_state=assistant_state,
            summary_length=summary_length,
            summary=cached_summary,
        )
        assistant_state.store_refined_summary(summary_length, cached_summary)

        return {
            **state,
            "assistant_state": assistant_state,
            "response": cached_summary,
            "context_source": summary_length.value,
            "model_used": f"Refinement ({self._model_gateway.refiner_model_name})",
        }

    @staticmethod
    def _enforce_refinement_order(
        assistant_state: AssistantState,
        summary_length: SummaryLength,
        summary: str,
    ) -> str:
        draft_summary = assistant_state.draft_summary or summary
        min_words, max_words = refinement_word_bounds(summary_length)
        candidate = coerce_summary_to_word_bounds(
            summary_text=summary,
            source_text=draft_summary,
            min_words=min_words,
            max_words=max_words,
        )
        candidate_words = word_count(candidate)

        if summary_length is SummaryLength.SHORT:
            if candidate_words > max_words or candidate in {assistant_state.medium_summary, assistant_state.long_summary}:
                candidate = extractive_summary_from_source(assistant_state.original_text, summary_length)
        elif summary_length is SummaryLength.MEDIUM:
            lower_bound = assistant_state.short_summary and word_count(assistant_state.short_summary) >= min_words
            upper_bound = assistant_state.long_summary and word_count(assistant_state.long_summary) <= max_words
            if candidate_words < min_words or candidate_words > max_words or candidate == assistant_state.short_summary or candidate == assistant_state.long_summary:
                candidate = extractive_summary_from_source(assistant_state.original_text, summary_length)
            elif lower_bound and candidate_words <= word_count(assistant_state.short_summary):
                candidate = extractive_summary_from_source(assistant_state.original_text, summary_length)
            elif upper_bound and candidate_words >= word_count(assistant_state.long_summary):
                candidate = extractive_summary_from_source(assistant_state.original_text, summary_length)
        else:
            if candidate_words < min_words or candidate in {assistant_state.short_summary, assistant_state.medium_summary}:
                candidate = extractive_summary_from_source(assistant_state.original_text, summary_length)

        return coerce_summary_to_word_bounds(
            summary_text=candidate,
            source_text=assistant_state.original_text,
            min_words=max(1, min_words),
            max_words=max(1, max_words),
        )

    def _qa_node(self, state: WorkflowState) -> WorkflowState:
        assistant_state = state["assistant_state"]
        if assistant_state.current_summary is None and assistant_state.draft_summary is None:
            artifacts = self._model_gateway.generate_draft_summary(assistant_state.original_text)
            assistant_state.store_draft_summary(artifacts)

        context_source, context = assistant_state.build_qa_context(
            query=state["query"],
            qa_chunk_word_limit=self._model_gateway.qa_chunk_word_limit,
            qa_chunk_overlap_paragraphs=self._model_gateway.qa_chunk_overlap_paragraphs,
            qa_max_chunks=self._model_gateway.qa_max_chunks,
        )
        response = self._qa_client.answer_question(context=context, question=state["query"])

        return {
            **state,
            "assistant_state": assistant_state,
            "response": response.answer,
            "context_source": context_source,
            "model_used": f"QA ({self._qa_client.model_name})",
        }

    @staticmethod
    def _exit_node(state: WorkflowState) -> WorkflowState:
        return {
            **state,
            "response": "Exiting assistant.",
            "context_source": "none",
            "model_used": "None",
        }
