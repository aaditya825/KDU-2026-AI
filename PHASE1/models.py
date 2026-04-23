from dataclasses import dataclass
from enum import Enum
from typing import Dict, List


class RouteLabel(str, Enum):
    CASUAL_CONVERSATION = "casual_conversation"
    COMPLEX_CODE_GENERATION = "complex_code_generation"


@dataclass(frozen=True)
class SemanticRouteResult:
    predicted_label: RouteLabel
    confidence: float
    top_score: float
    second_score: float
    all_scores: Dict[str, float]


@dataclass(frozen=True)
class LLMRouteResult:
    route: RouteLabel
    confidence: float
    reason: str
    model_id: str
    usage: dict


@dataclass(frozen=True)
class FinalRouteDecision:
    route: RouteLabel
    source: str
    metadata: dict


@dataclass(frozen=True)
class ModelResponse:
    model_id: str
    text: str
    usage: dict


@dataclass(frozen=True)
class RouteContext:
    prototypes: Dict[RouteLabel, List[str]]
    route_to_model: Dict[RouteLabel, str]
