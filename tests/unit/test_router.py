from pathlib import Path

from src.classifier.classifier import QueryClassifier
from src.config_loader.config_loader import ConfigLoader
from src.router.routing_engine import RoutingEngine


def _load_configs():
    loader = ConfigLoader(
        config_path=Path("configs/config.yaml"),
        pricing_path=Path("configs/pricing.yaml"),
    )
    return loader.load(), loader.load_pricing()


def test_router_uses_rule_match_for_faq() -> None:
    active_config, pricing = _load_configs()
    classification = QueryClassifier().classify("What are your hours?")

    decision = RoutingEngine().decide(classification, active_config, pricing)

    assert decision.model_tier == "economy"
    assert decision.prompt_key == "faq"
    assert decision.prompt_version == 1


def test_router_uses_low_confidence_fallback_tier() -> None:
    active_config, pricing = _load_configs()
    classification = QueryClassifier().classify(
        "I need help and I'm not sure whether to cancel or reschedule"
    )

    decision = RoutingEngine().decide(classification, active_config, pricing)

    assert decision.model_tier == "balanced"
    assert decision.model_id == "gemini-2.5-flash"
    assert decision.estimated_cost > 0
