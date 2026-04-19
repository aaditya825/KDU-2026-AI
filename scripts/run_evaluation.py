"""Run the local evaluation workflow and emit report artifacts."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.evaluator import EvaluationRunner


def main() -> None:
    runner = EvaluationRunner(
        dataset_path=PROJECT_ROOT / "sample_data" / "queries.csv",
        reports_dir=PROJECT_ROOT / "reports",
        project_root=PROJECT_ROOT,
    )
    report = runner.run()
    print(
        "Evaluation complete: "
        f"overall_accuracy={report['summary']['overall_accuracy']}, "
        f"average_actual_cost_usd={report['summary']['average_actual_cost_usd']}"
    )


if __name__ == "__main__":
    main()
