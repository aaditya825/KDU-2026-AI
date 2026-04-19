import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from src.api.service import FixItApplication, build_local_application
from src.config_loader.config_loader import ConfigManager
from src.classifier.classifier import QueryClassifier
from src.config_loader.config_loader import ConfigLoader
from src.core.models import CostUsageRecord
from src.llm_client.client import LLMClient
from src.prompt_manager.metadata_tracker import PromptMetadataTracker
from src.prompt_manager.prompt_manager import PromptManager
from src.router.routing_engine import RoutingEngine


def test_pipeline_flow_resolves_booking_prompt() -> None:
    loader = ConfigLoader(
        config_path=Path("configs/config.yaml"),
        pricing_path=Path("configs/pricing.yaml"),
    )
    active_config = loader.load()
    pricing = loader.load_pricing()
    classifier = QueryClassifier()
    router = RoutingEngine()
    prompt_manager = PromptManager(Path("prompts"))

    classification = classifier.classify("Can I reschedule my cleaning appointment?")
    decision = router.decide(classification, active_config, pricing)
    prompt = prompt_manager.load(decision.prompt_key, decision.prompt_version)
    rendered = prompt_manager.render(
        prompt,
        {"query": "Can I reschedule my cleaning appointment?"},
    )

    assert classification.category == "booking"
    assert decision.model_tier == "balanced"
    assert "Can I reschedule my cleaning appointment?" in rendered


def test_application_handles_query_end_to_end() -> None:
    sandbox_dir = Path.cwd() / f"app-end-to-end-test-{uuid4().hex}"
    sandbox_dir.mkdir(parents=True, exist_ok=False)
    try:
        _seed_sandbox_project(sandbox_dir)
        app = _build_sandbox_application(sandbox_dir, LLMClient(provider_mode="mock"))

        result = app.handle_query("My plumber didn't show up, need refund")

        assert result.category == "complaint"
        assert result.model_tier == "premium"
        assert result.actual_cost > 0
        assert "need refund" in result.response_text
    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)


def test_application_persists_prompt_runtime_metadata() -> None:
    sandbox_dir = Path.cwd() / f"app-prompt-metadata-test-{uuid4().hex}"
    sandbox_dir.mkdir(parents=True, exist_ok=False)
    try:
        (sandbox_dir / "configs").mkdir()
        (sandbox_dir / "prompts").mkdir()
        (sandbox_dir / "prompts" / "faq").mkdir(parents=True)
        (sandbox_dir / "prompts" / "booking").mkdir(parents=True)
        (sandbox_dir / "prompts" / "complaint").mkdir(parents=True)
        (sandbox_dir / "prompts" / "base").mkdir(parents=True)
        (sandbox_dir / "data").mkdir()

        for relative_file in [
            Path("configs/config.yaml"),
            Path("configs/pricing.yaml"),
            Path("prompts/faq/v1.yaml"),
            Path("prompts/booking/v1.yaml"),
            Path("prompts/complaint/v1.yaml"),
            Path("prompts/base/v1.yaml"),
        ]:
            destination = sandbox_dir / relative_file
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(relative_file.read_text(encoding="utf-8"), encoding="utf-8")

        (sandbox_dir / "data" / "prompt_metrics.json").write_text("{}", encoding="utf-8")

        app = _build_sandbox_application(sandbox_dir, LLMClient(provider_mode="mock"))
        result = app.handle_query("What are your hours?")

        metrics_store = json.loads(
            (sandbox_dir / "data" / "prompt_metrics.json").read_text(encoding="utf-8")
        )

        assert metrics_store["faq:1"]["usage_count"] == 1
        assert metrics_store["faq:1"]["success_count"] == 1
        assert result.metadata["prompt_runtime_metadata"]["usage_count"] == 1
    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)


def test_application_warning_budget_downgrades_premium_to_balanced() -> None:
    sandbox_dir = Path.cwd() / f"app-warning-budget-test-{uuid4().hex}"
    sandbox_dir.mkdir(parents=True, exist_ok=False)
    try:
        _seed_sandbox_project(sandbox_dir)
        app = _build_sandbox_application(sandbox_dir, LLMClient(provider_mode="mock"))
        app.cost_tracker.record(
            CostUsageRecord(
                query_id="near-warning",
                model_id="mock-economy",
                estimated_cost=0.0,
                actual_cost=12.0,
                usage_details={"total_tokens": 100},
                timestamp=datetime.now(UTC),
            )
        )

        result = app.handle_query("My plumber didn't show up, need refund")

        assert result.mode == "warning"
        assert result.model_tier == "balanced"
        assert result.metadata["route_adjustment_reason"] is not None
    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)


def test_application_critical_budget_downgrades_balanced_to_economy() -> None:
    sandbox_dir = Path.cwd() / f"app-critical-budget-test-{uuid4().hex}"
    sandbox_dir.mkdir(parents=True, exist_ok=False)
    try:
        _seed_sandbox_project(sandbox_dir)
        app = _build_sandbox_application(sandbox_dir, LLMClient(provider_mode="mock"))
        app.cost_tracker.record(
            CostUsageRecord(
                query_id="near-critical",
                model_id="mock-economy",
                estimated_cost=0.0,
                actual_cost=15.0,
                usage_details={"total_tokens": 100},
                timestamp=datetime.now(UTC),
            )
        )

        result = app.handle_query("Can I reschedule my cleaning appointment?")

        assert result.mode == "critical"
        assert result.model_tier == "economy"
        assert result.metadata["route_adjustment_reason"] is not None
    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)


class PremiumFailingClient:
    def generate(self, prompt: str, model_id: str, **kwargs):
        if model_id == "gemini-2.5-pro":
            raise RuntimeError("premium model failed")
        return LLMClient(provider_mode="mock").generate(prompt, model_id, **kwargs)

    def classify_query(self, *, query: str, model_id: str, confidence_threshold: float):
        return LLMClient(provider_mode="mock").classify_query(
            query=query,
            model_id=model_id,
            confidence_threshold=confidence_threshold,
        )


class AlwaysFailingClient:
    def generate(self, prompt: str, model_id: str, **kwargs):
        raise RuntimeError(f"{model_id} failed")

    def classify_query(self, *, query: str, model_id: str, confidence_threshold: float):
        raise RuntimeError(f"{model_id} classification failed")


class HybridClassificationClient:
    def generate(self, prompt: str, model_id: str, **kwargs):
        return LLMClient(provider_mode="mock").generate(prompt, model_id, **kwargs)

    def classify_query(self, *, query: str, model_id: str, confidence_threshold: float):
        return LLMClient(provider_mode="mock").classify_query(
            query=query,
            model_id=model_id,
            confidence_threshold=confidence_threshold,
        ).model_copy(
            update={
                "category": "complaint",
                "complexity": "high",
                "expected_response_type": "complex",
                "confidence": 0.78,
                "source": "gemini-classifier",
                "model_id": model_id,
            }
        )


def _build_sandbox_application(sandbox_dir: Path, llm_client) -> FixItApplication:
    loader = ConfigLoader(
        config_path=sandbox_dir / "configs" / "config.yaml",
        pricing_path=sandbox_dir / "configs" / "pricing.yaml",
    )
    return FixItApplication(
        config_manager=ConfigManager(loader),
        classifier=QueryClassifier(llm_client=llm_client),
        router=RoutingEngine(),
        prompt_manager=PromptManager(
            sandbox_dir / "prompts",
            metadata_tracker=PromptMetadataTracker(sandbox_dir / "data" / "prompt_metrics.json"),
        ),
        llm_client=llm_client,
    )


def _seed_sandbox_project(sandbox_dir: Path) -> None:
    (sandbox_dir / "configs").mkdir(parents=True, exist_ok=True)
    (sandbox_dir / "prompts").mkdir(parents=True, exist_ok=True)
    (sandbox_dir / "prompts" / "faq").mkdir(parents=True, exist_ok=True)
    (sandbox_dir / "prompts" / "booking").mkdir(parents=True, exist_ok=True)
    (sandbox_dir / "prompts" / "complaint").mkdir(parents=True, exist_ok=True)
    (sandbox_dir / "prompts" / "base").mkdir(parents=True, exist_ok=True)
    (sandbox_dir / "data").mkdir(parents=True, exist_ok=True)

    for relative_file in [
        Path("configs/config.yaml"),
        Path("configs/pricing.yaml"),
        Path("prompts/faq/v1.yaml"),
        Path("prompts/booking/v1.yaml"),
        Path("prompts/complaint/v1.yaml"),
        Path("prompts/base/v1.yaml"),
    ]:
        destination = sandbox_dir / relative_file
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(relative_file.read_text(encoding="utf-8"), encoding="utf-8")

    (sandbox_dir / "data" / "prompt_metrics.json").write_text("{}", encoding="utf-8")


def test_application_falls_back_to_base_prompt_when_selected_prompt_missing() -> None:
    sandbox_dir = Path.cwd() / f"app-prompt-fallback-test-{uuid4().hex}"
    sandbox_dir.mkdir(parents=True, exist_ok=False)
    try:
        _seed_sandbox_project(sandbox_dir)
        config_path = sandbox_dir / "configs" / "config.yaml"
        updated = config_path.read_text(encoding="utf-8").replace("prompt_key: faq", "prompt_key: missing-faq")
        config_path.write_text(updated, encoding="utf-8")

        app = _build_sandbox_application(sandbox_dir, LLMClient(provider_mode="mock"))
        result = app.handle_query("What are your hours?")

        assert result.prompt_key == "base"
        assert result.metadata["prompt_fallback_reason"] is not None
    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)


def test_application_retries_on_cheaper_tier_when_generation_fails() -> None:
    sandbox_dir = Path.cwd() / f"app-generation-fallback-test-{uuid4().hex}"
    sandbox_dir.mkdir(parents=True, exist_ok=False)
    try:
        _seed_sandbox_project(sandbox_dir)
        app = _build_sandbox_application(sandbox_dir, PremiumFailingClient())

        result = app.handle_query("My plumber didn't show up, need refund")

        assert result.model_tier == "balanced"
        assert result.metadata["generation_fallback_reason"] is not None
        assert result.mode != "degraded"
    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)


def test_application_returns_local_degraded_response_when_all_models_fail() -> None:
    sandbox_dir = Path.cwd() / f"app-local-degraded-test-{uuid4().hex}"
    sandbox_dir.mkdir(parents=True, exist_ok=False)
    try:
        _seed_sandbox_project(sandbox_dir)
        app = _build_sandbox_application(sandbox_dir, AlwaysFailingClient())

        result = app.handle_query("Can I reschedule my cleaning appointment?")

        assert result.mode == "degraded"
        assert result.metadata["final_response_source"] == "local-fallback"
        assert "temporarily unable to process" in result.response_text
        assert result.metadata["generation_fallback_reason"] is not None
    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)


def test_application_uses_hybrid_classifier_config_for_conflicting_query() -> None:
    sandbox_dir = Path.cwd() / f"app-hybrid-classifier-test-{uuid4().hex}"
    sandbox_dir.mkdir(parents=True, exist_ok=False)
    try:
        _seed_sandbox_project(sandbox_dir)
        config_path = sandbox_dir / "configs" / "config.yaml"
        updated = config_path.read_text(encoding="utf-8").replace(
            "mode: rule_based",
            "mode: hybrid",
        )
        config_path.write_text(updated, encoding="utf-8")

        app = _build_sandbox_application(sandbox_dir, HybridClassificationClient())
        result = app.handle_query("Can I cancel my booking and get a refund?")

        assert result.category == "complaint"
        assert result.metadata["classification_source"] == "gemini-classifier"
        assert result.metadata["classification_actual_cost_usd"] > 0
    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)
