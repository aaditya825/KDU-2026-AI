from datetime import UTC, datetime
from pathlib import Path

from src.config_loader.config_loader import ConfigLoader
from src.core.models import CostUsageRecord
from src.cost_control.cost_tracker import CostTracker


def _build_tracker() -> CostTracker:
    loader = ConfigLoader(
        config_path=Path("configs/config.yaml"),
        pricing_path=Path("configs/pricing.yaml"),
    )
    config = loader.load()
    pricing = loader.load_pricing()
    return CostTracker(pricing_config=pricing, cost_limits=config.cost_limits)


def test_cost_tracker_records_usage_totals() -> None:
    tracker = _build_tracker()
    tracker.record(
        CostUsageRecord(
            query_id="q-1",
            model_id="mock-economy",
            estimated_cost=0.01,
            actual_cost=0.02,
            usage_details={"total_tokens": 100},
            timestamp=datetime.now(UTC),
        )
    )

    assert tracker.get_daily_total() == 0.02
    assert tracker.get_monthly_total() == 0.02


def test_cost_tracker_flags_degraded_when_budget_exceeded() -> None:
    tracker = _build_tracker()

    result = tracker.check_budget(projected_additional_cost=1000.0)

    assert result.mode == "degraded"
    assert result.reason == "budget limit exceeded"


def test_cost_tracker_flags_warning_when_threshold_reached() -> None:
    tracker = _build_tracker()
    tracker.record(
        CostUsageRecord(
            query_id="q-warning",
            model_id="mock-economy",
            estimated_cost=0.0,
            actual_cost=12.0,
            usage_details={"total_tokens": 100},
            timestamp=datetime.now(UTC),
        )
    )

    result = tracker.check_budget(projected_additional_cost=0.01)

    assert result.mode == "warning"
    assert result.reason == "warning budget threshold reached"


def test_cost_tracker_flags_critical_when_threshold_reached() -> None:
    tracker = _build_tracker()
    tracker.record(
        CostUsageRecord(
            query_id="q-critical",
            model_id="mock-economy",
            estimated_cost=0.0,
            actual_cost=15.0,
            usage_details={"total_tokens": 100},
            timestamp=datetime.now(UTC),
        )
    )

    result = tracker.check_budget(projected_additional_cost=0.01)

    assert result.mode == "critical"
    assert result.reason == "critical budget threshold reached"
