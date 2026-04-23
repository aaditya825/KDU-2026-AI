from abc import ABC, abstractmethod

from models import FinalRouteDecision, LLMRouteResult, ModelResponse, SemanticRouteResult


class ISemanticRouter(ABC):
    @abstractmethod
    def predict(self, query: str) -> SemanticRouteResult:
        pass


class ILLMRouter(ABC):
    @abstractmethod
    def route(self, query: str) -> LLMRouteResult:
        pass


class IModelInvoker(ABC):
    @abstractmethod
    def invoke(self, model_id: str, user_query: str) -> ModelResponse:
        pass


class IRoutingOrchestrator(ABC):
    @abstractmethod
    def handle(self, user_query: str) -> tuple[FinalRouteDecision, ModelResponse]:
        pass
