"""In-memory cost tracker implementation."""

from __future__ import annotations

from datetime import UTC, datetime

from src.core.models import (
    BudgetCheckResult,
    CostLimits,
    CostUsageRecord,
    ModelTierConfig,
    PricingConfig,
)


class CostTracker:
    """Tracks projected and actual spend against configured thresholds."""

    def __init__(self, pricing_config: PricingConfig, cost_limits: CostLimits) -> None:
        self.pricing_config = pricing_config
        self.cost_limits = cost_limits
        self.records: list[CostUsageRecord] = []

    def estimate_cost(
        self,
        tier_config: ModelTierConfig,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        pricing = self.pricing_config.providers[tier_config.provider].models[tier_config.model_id]
        estimated = (
            (prompt_tokens / 1000) * pricing.input_cost_per_1k_tokens_usd
            + (completion_tokens / 1000) * pricing.output_cost_per_1k_tokens_usd
        )
        return round(estimated, 6)

    def check_budget(self, projected_additional_cost: float) -> BudgetCheckResult:
        daily_total = self.get_daily_total() + projected_additional_cost
        monthly_total = self.get_monthly_total() + projected_additional_cost

        if (
            daily_total > self.cost_limits.daily_usd
            or monthly_total > self.cost_limits.monthly_usd
        ):
            return BudgetCheckResult(
                mode="degraded",
                reason="budget limit exceeded",
                projected_daily_total=round(daily_total, 6),
                projected_monthly_total=round(monthly_total, 6),
            )

        if (
            daily_total >= self.cost_limits.daily_usd * self.cost_limits.critical_threshold_ratio
            or monthly_total
            >= self.cost_limits.monthly_usd * self.cost_limits.critical_threshold_ratio
        ):
            return BudgetCheckResult(
                mode="critical",
                reason="critical budget threshold reached",
                projected_daily_total=round(daily_total, 6),
                projected_monthly_total=round(monthly_total, 6),
            )

        if (
            daily_total >= self.cost_limits.daily_usd * self.cost_limits.warning_threshold_ratio
            or monthly_total
            >= self.cost_limits.monthly_usd * self.cost_limits.warning_threshold_ratio
        ):
            return BudgetCheckResult(
                mode="warning",
                reason="warning budget threshold reached",
                projected_daily_total=round(daily_total, 6),
                projected_monthly_total=round(monthly_total, 6),
            )

        return BudgetCheckResult(
            mode="normal",
            reason=None,
            projected_daily_total=round(daily_total, 6),
            projected_monthly_total=round(monthly_total, 6),
        )

    def record(self, record: CostUsageRecord) -> None:
        """Record a usage event."""
        self.records.append(record)

    def get_daily_total(self, at_time: datetime | None = None) -> float:
        reference = at_time or datetime.now(UTC)
        total = sum(
            record.actual_cost
            for record in self.records
            if record.timestamp.date() == reference.date()
        )
        return round(total, 6)

    def get_monthly_total(self, at_time: datetime | None = None) -> float:
        reference = at_time or datetime.now(UTC)
        total = sum(
            record.actual_cost
            for record in self.records
            if record.timestamp.year == reference.year
            and record.timestamp.month == reference.month
        )
        return round(total, 6)
