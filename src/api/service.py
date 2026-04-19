"""Application orchestration for end-to-end local query handling."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from src.classifier.classifier import QueryClassifier
from src.config_loader.config_loader import ConfigLoader, ConfigManager
from src.core.env import load_dotenv
from src.core.models import (
    BudgetCheckResult,
    ClassificationResult,
    CostUsageRecord,
    GenerationResult,
    QueryResponse,
    QueryInput,
    RoutingDecision,
)
from src.cost_control.cost_tracker import CostTracker
from src.llm_client.client import LLMClient
from src.prompt_manager.metadata_tracker import PromptMetadataTracker
from src.prompt_manager.prompt_manager import PromptManager
from src.router.routing_engine import RoutingEngine


class FixItApplication:
    """Coordinates the local end-to-end query flow."""

    def __init__(
        self,
        config_manager: ConfigManager,
        classifier: QueryClassifier,
        router: RoutingEngine,
        prompt_manager: PromptManager,
        llm_client: LLMClient,
    ) -> None:
        self.config_manager = config_manager
        self.classifier = classifier
        self.router = router
        self.prompt_manager = prompt_manager
        self.llm_client = llm_client

        self.active_config, self.pricing_config = self.config_manager.get_current()
        self.cost_tracker = CostTracker(
            pricing_config=self.pricing_config,
            cost_limits=self.active_config.cost_limits,
        )

    def handle_query(self, query: str, query_id: str | None = None) -> QueryResponse:
        """Process a query through the local pipeline."""
        query_input = QueryInput(
            query=query,
            query_id=query_id or str(uuid4()),
            timestamp=datetime.now(UTC),
        )
        self.active_config, self.pricing_config = self.config_manager.get_current()
        self.cost_tracker.pricing_config = self.pricing_config
        self.cost_tracker.cost_limits = self.active_config.cost_limits

        classification = self.classifier.classify(query_input.query, self.active_config)
        classification_estimated_cost = self._estimate_classification_cost(
            classification=classification,
            query=query_input.query,
            use_actual_usage=False,
        )
        decision = self.router.decide(
            classification=classification,
            active_config=self.active_config,
            pricing_config=self.pricing_config,
        )
        prompt, prompt_fallback_reason = self.prompt_manager.load_with_fallback(
            decision.prompt_key,
            decision.prompt_version,
            fallback_key=self.active_config.routing.default_prompt_key,
            fallback_version=self.active_config.routing.default_prompt_version,
        )
        rendered_prompt = self.prompt_manager.render(prompt, {"query": query_input.query})
        estimated_cost = self._estimate_request_cost(
            decision=decision,
            rendered_prompt=rendered_prompt,
            query=query_input.query,
        )
        estimated_cost += classification_estimated_cost
        budget_check = self.cost_tracker.check_budget(estimated_cost)

        effective_decision, route_adjustment_reason = self._apply_budget_policy(
            classification=classification,
            decision=decision,
            budget_check=budget_check,
        )
        if effective_decision != decision:
            prompt, prompt_fallback_reason = self.prompt_manager.load_with_fallback(
                effective_decision.prompt_key,
                effective_decision.prompt_version,
                fallback_key=self.active_config.routing.default_prompt_key,
                fallback_version=self.active_config.routing.default_prompt_version,
            )
            rendered_prompt = self.prompt_manager.render(prompt, {"query": query_input.query})
            estimated_cost = self._estimate_request_cost(
                decision=effective_decision,
                rendered_prompt=rendered_prompt,
                query=query_input.query,
            )
            estimated_cost += classification_estimated_cost

        if self.prompt_manager.metadata_tracker is not None:
            prompt.runtime_metadata = self.prompt_manager.metadata_tracker.record_usage(
                prompt.key,
                prompt.version,
            )

        generation, effective_decision, generation_fallback_reason, response_mode = self._generate_with_fallback(
            classification=classification,
            decision=effective_decision,
            rendered_prompt=rendered_prompt,
            query=query_input.query,
            mode=budget_check.mode,
        )
        generation_latency_ms = generation.usage_details.get("latency_ms", 0.0)
        estimated_cost = self._estimate_request_cost(
            decision=effective_decision,
            rendered_prompt=rendered_prompt,
            query=query_input.query,
        )
        estimated_cost += classification_estimated_cost

        generation_actual_cost = self.cost_tracker.estimate_cost(
            tier_config=self.active_config.models.tiers[effective_decision.model_tier],
            prompt_tokens=generation.usage_details.get("prompt_tokens", 0),
            completion_tokens=generation.usage_details.get("completion_tokens", 0),
        )
        classification_actual_cost = self._estimate_classification_cost(
            classification=classification,
            query=query_input.query,
            use_actual_usage=True,
        )
        actual_cost = generation_actual_cost + classification_actual_cost
        self.cost_tracker.record(
            CostUsageRecord(
                query_id=query_input.query_id,
                model_id=effective_decision.model_id,
                estimated_cost=estimated_cost,
                actual_cost=actual_cost,
                usage_details={
                    **generation.usage_details,
                    "classification_source": classification.source,
                    "classification_model_id": classification.model_id,
                    "classification_usage_details": classification.usage_details,
                    "classification_estimated_cost_usd": classification_estimated_cost,
                    "classification_actual_cost_usd": classification_actual_cost,
                },
                timestamp=query_input.timestamp,
            )
        )
        updated_prompt_runtime_metadata = prompt.runtime_metadata
        if self.prompt_manager.metadata_tracker is not None:
            updated_prompt_runtime_metadata = self.prompt_manager.metadata_tracker.record_outcome(
                prompt.key,
                prompt.version,
                success=generation.provider != "local-fallback",
                actual_cost=actual_cost,
                latency_ms=generation_latency_ms,
            )

        return QueryResponse(
            query_id=query_input.query_id,
            category=classification.category,
            complexity=classification.complexity,
            response_text=generation.text,
            model_id=effective_decision.model_id,
            model_tier=effective_decision.model_tier,
            prompt_key=prompt.key,
            prompt_version=prompt.version,
            estimated_cost=estimated_cost,
            actual_cost=actual_cost,
            mode=response_mode,
            metadata={
                "confidence": classification.confidence,
                "budget_reason": budget_check.reason,
                "projected_daily_total": budget_check.projected_daily_total,
                "projected_monthly_total": budget_check.projected_monthly_total,
                "usage_details": generation.usage_details,
                "classification_source": classification.source,
                "classification_model_id": classification.model_id,
                "classification_fallback_reason": classification.fallback_reason,
                "classification_usage_details": classification.usage_details,
                "classification_estimated_cost_usd": classification_estimated_cost,
                "classification_actual_cost_usd": classification_actual_cost,
                "route_adjustment_reason": route_adjustment_reason,
                "prompt_fallback_reason": prompt_fallback_reason,
                "generation_fallback_reason": generation_fallback_reason,
                "final_response_source": generation.provider,
                "prompt_runtime_metadata": updated_prompt_runtime_metadata.model_dump(),
            },
        )

    def _estimate_request_cost(
        self,
        *,
        decision: RoutingDecision,
        rendered_prompt: str,
        query: str,
    ) -> float:
        tier_config = self.active_config.models.tiers[decision.model_tier]
        return self.cost_tracker.estimate_cost(
            tier_config=tier_config,
            prompt_tokens=max(1, len(rendered_prompt.split())),
            completion_tokens=max(12, len(query.split()) + 8),
        )

    def _estimate_classification_cost(
        self,
        *,
        classification: ClassificationResult,
        query: str,
        use_actual_usage: bool,
    ) -> float:
        if classification.source == "rule-based":
            return 0.0

        provider_name = self.active_config.classifier.provider
        provider_pricing = self.pricing_config.providers.get(provider_name)
        if provider_pricing is None:
            return 0.0

        model_id = classification.model_id or self.active_config.classifier.model_id
        model_pricing = provider_pricing.models.get(model_id)
        if model_pricing is None:
            return 0.0

        if use_actual_usage:
            prompt_tokens = classification.usage_details.get("prompt_tokens", 0)
            completion_tokens = classification.usage_details.get("completion_tokens", 0)
        else:
            prompt_tokens = max(24, len(query.split()) + 20)
            completion_tokens = 24

        return round(
            (prompt_tokens / 1000 * model_pricing.input_cost_per_1k_tokens_usd)
            + (completion_tokens / 1000 * model_pricing.output_cost_per_1k_tokens_usd),
            6,
        )

    def _apply_budget_policy(
        self,
        *,
        classification: ClassificationResult,
        decision: RoutingDecision,
        budget_check: BudgetCheckResult,
    ) -> tuple[RoutingDecision, str | None]:
        if budget_check.mode == "normal":
            return decision, None

        if budget_check.mode == "warning":
            if decision.model_tier == "premium" and "balanced" in self.active_config.models.tiers:
                downgraded = self._with_tier(decision, "balanced")
                return downgraded, "downgraded from premium to balanced due to warning budget threshold"
            return decision, "warning budget threshold reached; existing route retained"

        if budget_check.mode == "critical":
            if classification.category == "complaint" or classification.complexity == "high":
                target_tier = "balanced" if "balanced" in self.active_config.models.tiers else self.active_config.models.default_tier
            else:
                target_tier = self.active_config.models.default_tier

            downgraded = self._with_tier(decision, target_tier)
            if downgraded != decision:
                return downgraded, f"downgraded to {target_tier} due to critical budget threshold"
            return decision, "critical budget threshold reached; existing route already minimal for policy"

        cheapest_tier_name = self.active_config.models.default_tier
        degraded = decision.model_copy(
            update={
                "model_tier": cheapest_tier_name,
                "model_id": self.active_config.models.tiers[cheapest_tier_name].model_id,
                "prompt_key": self.active_config.routing.default_prompt_key,
                "prompt_version": self.active_config.routing.default_prompt_version,
            }
        )
        return degraded, "degraded mode applied due to budget limit exceeded"

    def _with_tier(self, decision: RoutingDecision, tier_name: str) -> RoutingDecision:
        tier = self.active_config.models.tiers[tier_name]
        return decision.model_copy(
            update={
                "model_tier": tier_name,
                "model_id": tier.model_id,
            }
        )

    def _generate_with_fallback(
        self,
        *,
        classification: ClassificationResult,
        decision: RoutingDecision,
        rendered_prompt: str,
        query: str,
        mode: str,
    ) -> tuple[GenerationResult, RoutingDecision, str | None, str]:
        generation_started_at = perf_counter()
        try:
            generation = self.llm_client.generate(
                prompt=rendered_prompt,
                model_id=decision.model_id,
                query=query,
                category=classification.category,
                mode=mode,
            )
            generation.usage_details["latency_ms"] = round(
                (perf_counter() - generation_started_at) * 1000,
                3,
            )
            return generation, decision, None, mode
        except RuntimeError as exc:
            last_error = str(exc)

        for fallback_tier in self._fallback_tiers_for_generation(decision.model_tier):
            fallback_decision = self._with_tier(decision, fallback_tier)
            retry_started_at = perf_counter()
            try:
                generation = self.llm_client.generate(
                    prompt=rendered_prompt,
                    model_id=fallback_decision.model_id,
                    query=query,
                    category=classification.category,
                    mode="degraded" if mode == "degraded" else mode,
                )
                generation.usage_details["latency_ms"] = round(
                    (perf_counter() - retry_started_at) * 1000,
                    3,
                )
                return (
                    generation,
                    fallback_decision,
                    (
                        f"generation failed for {decision.model_id}: {last_error}; "
                        f"retried successfully with {fallback_decision.model_id}"
                    ),
                    mode,
                )
            except RuntimeError as exc:
                last_error = str(exc)

        degraded_generation = GenerationResult(
            model_id="local-degraded-response",
            provider="local-fallback",
            text=(
                "We are temporarily unable to process your request with an AI model. "
                f"Please try again shortly. Error reason: {last_error}"
            ),
            usage_details={
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "latency_ms": 0.0,
            },
        )
        return (
            degraded_generation,
            self._with_tier(decision, self.active_config.models.default_tier),
            f"all model generation attempts failed; returned local degraded response. last_error={last_error}",
            "degraded",
        )

    def _fallback_tiers_for_generation(self, current_tier: str) -> list[str]:
        current_cost = self._tier_cost_score(current_tier)
        cheaper_tiers = [
            tier_name
            for tier_name in self.active_config.models.tiers
            if tier_name != current_tier and self._tier_cost_score(tier_name) < current_cost
        ]
        return sorted(cheaper_tiers, key=self._tier_cost_score, reverse=True)

    def _tier_cost_score(self, tier_name: str) -> float:
        tier = self.active_config.models.tiers[tier_name]
        pricing = self.pricing_config.providers[tier.provider].models[tier.model_id]
        return pricing.input_cost_per_1k_tokens_usd + pricing.output_cost_per_1k_tokens_usd


def build_local_application(project_root: Path | None = None) -> FixItApplication:
    """Construct the local app with filesystem-backed config and prompts."""
    root = project_root or Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")

    loader = ConfigLoader(
        config_path=root / "configs" / "config.yaml",
        pricing_path=root / "configs" / "pricing.yaml",
    )
    manager = ConfigManager(loader)
    metadata_tracker = PromptMetadataTracker(root / "data" / "prompt_metrics.json")
    llm_client = LLMClient(
        provider_mode=os.getenv("PROVIDER_MODE", "mock"),
        api_key=os.getenv("GEMINI_API_KEY"),
        base_url=os.getenv(
            "GEMINI_API_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta",
        ),
        timeout_seconds=int(os.getenv("GEMINI_TIMEOUT_SECONDS", "30")),
    )
    return FixItApplication(
        config_manager=manager,
        classifier=QueryClassifier(llm_client=llm_client),
        router=RoutingEngine(),
        prompt_manager=PromptManager(
            root / "prompts",
            metadata_tracker=metadata_tracker,
        ),
        llm_client=llm_client,
    )
