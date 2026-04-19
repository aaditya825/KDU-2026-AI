"""Routing engine implementation."""

from __future__ import annotations

from src.core.models import ActiveConfig, ClassificationResult, PricingConfig, RoutingDecision


class RoutingEngine:
    """Selects model tier and prompt version for a query."""

    def decide(
        self,
        classification: ClassificationResult,
        active_config: ActiveConfig,
        pricing_config: PricingConfig,
    ) -> RoutingDecision:
        """Return the routing decision for a classified query."""
        selected_rule = None
        for rule in active_config.routing.rules:
            if (
                rule.category == classification.category
                and rule.complexity == classification.complexity
            ):
                selected_rule = rule
                break

        if selected_rule is None:
            tier_name = active_config.models.default_tier
            prompt_key = active_config.routing.default_prompt_key
            prompt_version = active_config.routing.default_prompt_version
        else:
            tier_name = selected_rule.route_to_tier
            prompt_key = selected_rule.prompt_key
            prompt_version = selected_rule.prompt_version

        if classification.confidence < 0.65:
            tier_name = active_config.routing.low_confidence_fallback_tier

        tier_config = active_config.models.tiers[tier_name]
        provider_pricing = pricing_config.providers[tier_config.provider]
        model_pricing = provider_pricing.models[tier_config.model_id]
        estimated_cost = (
            model_pricing.input_cost_per_1k_tokens_usd * 0.25
            + model_pricing.output_cost_per_1k_tokens_usd * 0.15
        )

        return RoutingDecision(
            model_tier=tier_name,
            model_id=tier_config.model_id,
            prompt_key=prompt_key,
            prompt_version=prompt_version,
            estimated_cost=round(estimated_cost, 6),
        )
