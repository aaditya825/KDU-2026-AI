from pathlib import Path

from src.classifier.classifier import QueryClassifier
from src.config_loader.config_loader import ConfigLoader
from src.core.models import ClassificationResult


class StubGeminiClassifierClient:
    def __init__(self, result: ClassificationResult) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def classify_query(self, *, query: str, model_id: str, confidence_threshold: float) -> ClassificationResult:
        self.calls.append(
            {
                "query": query,
                "model_id": model_id,
                "confidence_threshold": confidence_threshold,
            }
        )
        return self.result


class FailingGeminiClassifierClient:
    def classify_query(self, *, query: str, model_id: str, confidence_threshold: float) -> ClassificationResult:
        raise RuntimeError("classification endpoint failed")


def _load_active_config():
    return ConfigLoader(
        config_path=Path("configs/config.yaml"),
        pricing_path=Path("configs/pricing.yaml"),
    ).load()


def test_classifier_detects_faq_query() -> None:
    result = QueryClassifier().classify("What are your hours?")

    assert result.category == "FAQ"
    assert result.complexity == "low"
    assert result.expected_response_type == "simple"
    assert result.source == "rule-based"


def test_classifier_detects_complaint_query() -> None:
    result = QueryClassifier().classify("My plumber didn't show up, need refund")

    assert result.category == "complaint"
    assert result.complexity == "high"
    assert result.expected_response_type == "complex"


def test_classifier_detects_low_confidence_booking_query() -> None:
    result = QueryClassifier().classify(
        "I need help and I'm not sure whether to cancel or reschedule"
    )

    assert result.category == "booking"
    assert result.complexity == "medium"
    assert result.confidence < 0.65


def test_hybrid_classifier_uses_gemini_for_conflicting_query() -> None:
    active_config = _load_active_config().model_copy(
        update={
            "classifier": _load_active_config().classifier.model_copy(update={"mode": "hybrid"})
        }
    )
    client = StubGeminiClassifierClient(
        ClassificationResult(
            category="complaint",
            complexity="high",
            expected_response_type="complex",
            confidence=0.81,
            source="gemini-classifier",
            model_id="gemini-2.5-flash-lite",
            usage_details={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        )
    )

    result = QueryClassifier(llm_client=client).classify(
        "Can I cancel my booking and get a refund?",
        active_config,
    )

    assert result.source == "gemini-classifier"
    assert result.category == "complaint"
    assert client.calls[0]["model_id"] == "gemini-2.5-flash-lite"


def test_gemini_classifier_falls_back_to_rules_when_provider_fails() -> None:
    active_config = _load_active_config().model_copy(
        update={
            "classifier": _load_active_config().classifier.model_copy(update={"mode": "gemini"})
        }
    )

    result = QueryClassifier(llm_client=FailingGeminiClassifierClient()).classify(
        "Can I reschedule my cleaning appointment?",
        active_config,
    )

    assert result.source == "rule-based"
    assert result.category == "booking"
    assert result.fallback_reason is not None
