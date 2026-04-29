from __future__ import annotations

from app.services.comparison_service import ComparisonService, build_comparison_configs


def test_comparison_runs_all_stages_for_local_config():
    configs = build_comparison_configs(gemini_key="", openai_key="")
    service = ComparisonService(configs=configs)
    report = service.compare(file_id="f1", cleaned_text="Revenue grew by 20 percent year over year.")

    stages = {r["stage"] for r in report.model_results}
    assert stages == {"summary", "key_points", "topic_tags"}
    assert all("quality_notes" in r for r in report.model_results)
