import json
import shutil
from pathlib import Path
from uuid import uuid4

from src.evaluation.evaluator import EvaluationRunner


def _seed_evaluation_sandbox(sandbox_dir: Path) -> None:
    for relative_dir in [
        Path("configs"),
        Path("prompts/faq"),
        Path("prompts/booking"),
        Path("prompts/complaint"),
        Path("prompts/base"),
        Path("data"),
        Path("sample_data"),
        Path("reports"),
    ]:
        (sandbox_dir / relative_dir).mkdir(parents=True, exist_ok=True)

    for relative_file in [
        Path("configs/config.yaml"),
        Path("configs/pricing.yaml"),
        Path("prompts/faq/v1.yaml"),
        Path("prompts/booking/v1.yaml"),
        Path("prompts/complaint/v1.yaml"),
        Path("prompts/base/v1.yaml"),
        Path("sample_data/queries.csv"),
    ]:
        destination = sandbox_dir / relative_file
        destination.write_text(relative_file.read_text(encoding="utf-8"), encoding="utf-8")

    (sandbox_dir / "data" / "prompt_metrics.json").write_text("{}", encoding="utf-8")
    (sandbox_dir / ".env").write_text(
        "PROVIDER_MODE=mock\nDEFAULT_PROVIDER=gemini\nGEMINI_API_KEY=\n",
        encoding="utf-8",
    )


def test_evaluation_runner_generates_reports_and_summary() -> None:
    sandbox_dir = Path.cwd() / f"evaluation-test-{uuid4().hex}"
    sandbox_dir.mkdir(parents=True, exist_ok=False)
    try:
        _seed_evaluation_sandbox(sandbox_dir)
        runner = EvaluationRunner(
            dataset_path=sandbox_dir / "sample_data" / "queries.csv",
            reports_dir=sandbox_dir / "reports",
            project_root=sandbox_dir,
        )

        report = runner.run()

        assert report["total_cases"] == 8
        assert "overall_accuracy" in report["summary"]
        assert "average_actual_cost_usd" in report["summary"]
        assert (sandbox_dir / "reports" / "evaluation_report.json").exists()
        assert (sandbox_dir / "reports" / "evaluation_results.csv").exists()

        persisted = json.loads(
            (sandbox_dir / "reports" / "evaluation_report.json").read_text(encoding="utf-8")
        )
        assert persisted["total_cases"] == 8
        assert len(persisted["results"]) == 8
    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)
