from interfaces import ILLMRouter, IModelInvoker, IRoutingOrchestrator, ISemanticRouter
from models import FinalRouteDecision, ModelResponse, RouteContext


class RoutingOrchestrator(IRoutingOrchestrator):
    def __init__(
        self,
        semantic_router: ISemanticRouter,
        llm_router: ILLMRouter,
        model_invoker: IModelInvoker,
        route_context: RouteContext,
        semantic_threshold: float,
    ):
        self._semantic_router = semantic_router
        self._llm_router = llm_router
        self._model_invoker = model_invoker
        self._route_context = route_context
        self._semantic_threshold = semantic_threshold

    def handle(self, user_query: str) -> tuple[FinalRouteDecision, ModelResponse]:
        semantic_result = self._semantic_router.predict(user_query)

        if semantic_result.confidence >= self._semantic_threshold:
            final_decision = FinalRouteDecision(
                route=semantic_result.predicted_label,
                source="semantic_router",
                metadata={
                    "confidence": semantic_result.confidence,
                    "top_score": semantic_result.top_score,
                    "second_score": semantic_result.second_score,
                    "all_scores": semantic_result.all_scores,
                },
            )
        else:
            llm_result = self._llm_router.route(user_query)
            final_decision = FinalRouteDecision(
                route=llm_result.route,
                source="llm_router_fallback",
                metadata={
                    "semantic_confidence": semantic_result.confidence,
                    "llm_confidence": llm_result.confidence,
                    "reason": llm_result.reason,
                    "router_model_id": llm_result.model_id,
                    "router_usage": llm_result.usage,
                    "semantic_scores": semantic_result.all_scores,
                },
            )

        model_id = self._route_context.route_to_model[final_decision.route]
        model_response = self._model_invoker.invoke(model_id, user_query)

        return final_decision, model_response
