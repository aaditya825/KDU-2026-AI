from bedrock_client import BedrockModelInvoker
from config import AppConfig
from llm_router import BedrockLLMRouter
from models import RouteContext, RouteLabel
from orchestrator import RoutingOrchestrator
from semantic_router import EmbeddingSemanticRouter


def build_route_context() -> RouteContext:
    return RouteContext(
        prototypes={
            RouteLabel.CASUAL_CONVERSATION: [
                "casual chat",
                "simple conversation",
                "greeting or friendly message",
                "lightweight question answering",
                "short rewrite or summary",
                "easy non-technical request",
                "tiny python script",
                "simple hello world code",
            ],
            RouteLabel.COMPLEX_CODE_GENERATION: [
                "generate complex production code",
                "multi-step implementation",
                "framework-heavy coding task",
                "advanced debugging",
                "system design and architecture",
                "secure backend development",
                "large code generation task",
            ],
        },
        route_to_model={
            RouteLabel.CASUAL_CONVERSATION: AppConfig.CASUAL_MODEL_ID,
            RouteLabel.COMPLEX_CODE_GENERATION: AppConfig.COMPLEX_MODEL_ID,
        },
    )


def build_orchestrator() -> RoutingOrchestrator:
    route_context = build_route_context()

    semantic_router = EmbeddingSemanticRouter(
        embed_model_name=AppConfig.EMBED_MODEL_NAME,
        route_context=route_context,
    )

    llm_router = BedrockLLMRouter(
        aws_region=AppConfig.AWS_REGION,
        router_model_id=AppConfig.ROUTER_MODEL_ID,
    )

    model_invoker = BedrockModelInvoker(
        aws_region=AppConfig.AWS_REGION,
    )

    return RoutingOrchestrator(
        semantic_router=semantic_router,
        llm_router=llm_router,
        model_invoker=model_invoker,
        route_context=route_context,
        semantic_threshold=AppConfig.SEMANTIC_CONFIDENCE_THRESHOLD,
    )
