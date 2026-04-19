"""Local evaluation workflow over labeled query data."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from src.api.service import FixItApplication, build_local_application


class EvaluationRunner:
    """Runs the local pipeline against labeled evaluation data and emits reports."""

    def __init__(
        self,
        dataset_path: Path,
        reports_dir: Path,
        application: FixItApplication | None = None,
        project_root: Path | None = None,
    ) -> None:
        self.project_root = project_root or Path.cwd()
        self.dataset_path = dataset_path
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.application = application or build_local_application(self.project_root)

    def run(self) -> dict[str, Any]:
        """Execute evaluation and persist structured report artifacts."""
        rows = self._load_dataset()
        results: list[dict[str, Any]] = []

        for index, row in enumerate(rows, start=1):
            query = row["query"]
            response = self.application.handle_query(query, query_id=f"eval-{index}")
            result = self._evaluate_row(row, response)
            results.append(result)

        summary = self._build_summary(results)
        report = {
            "dataset_path": str(self.dataset_path),
            "total_cases": len(results),
            "summary": summary,
            "results": results,
        }
        self._write_report_files(report)
        return report

    def _load_dataset(self) -> list[dict[str, str]]:
        with self.dataset_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return list(reader)

    def _evaluate_row(self, row: dict[str, str], response) -> dict[str, Any]:
        expected_category = row["category"]
        expected_complexity = row["complexity"]
        expected_response_type = row["expected_response_type"]

        predicted_response_type = self._infer_response_type(response)
        category_match = response.category == expected_category
        complexity_match = response.complexity == expected_complexity
        response_type_match = predicted_response_type == expected_response_type

        return {
            "query_id": response.query_id,
            "query": row["query"],
            "expected": {
                "category": expected_category,
                "complexity": expected_complexity,
                "expected_response_type": expected_response_type,
            },
            "actual": {
                "category": response.category,
                "complexity": response.complexity,
                "predicted_response_type": predicted_response_type,
                "model_tier": response.model_tier,
                "model_id": response.model_id,
                "prompt_key": response.prompt_key,
                "prompt_version": response.prompt_version,
                "mode": response.mode,
                "estimated_cost": response.estimated_cost,
                "actual_cost": response.actual_cost,
            },
            "matches": {
                "category": category_match,
                "complexity": complexity_match,
                "response_type": response_type_match,
                "overall": category_match and complexity_match and response_type_match,
            },
            "metadata": response.metadata,
            "response_text": response.response_text,
        }

    @staticmethod
    def _infer_response_type(response) -> str:
        if response.complexity == "high" or response.category == "complaint":
            return "complex"
        if response.complexity == "low" and response.category == "FAQ":
            return "simple"
        return "standard"

    def _build_summary(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(results) or 1
        category_matches = sum(1 for result in results if result["matches"]["category"])
        complexity_matches = sum(1 for result in results if result["matches"]["complexity"])
        response_type_matches = sum(1 for result in results if result["matches"]["response_type"])
        overall_matches = sum(1 for result in results if result["matches"]["overall"])
        total_actual_cost = sum(result["actual"]["actual_cost"] for result in results)
        fallback_count = sum(
            1
            for result in results
            if result["metadata"].get("prompt_fallback_reason")
            or result["metadata"].get("generation_fallback_reason")
            or result["actual"]["mode"] == "degraded"
        )

        model_tier_counts: dict[str, int] = {}
        for result in results:
            tier = result["actual"]["model_tier"]
            model_tier_counts[tier] = model_tier_counts.get(tier, 0) + 1

        return {
            "category_accuracy": round(category_matches / total, 4),
            "complexity_accuracy": round(complexity_matches / total, 4),
            "response_type_accuracy": round(response_type_matches / total, 4),
            "overall_accuracy": round(overall_matches / total, 4),
            "average_actual_cost_usd": round(total_actual_cost / total, 6),
            "total_actual_cost_usd": round(total_actual_cost, 6),
            "fallback_rate": round(fallback_count / total, 4),
            "model_tier_distribution": model_tier_counts,
        }

    def _write_report_files(self, report: dict[str, Any]) -> None:
        json_path = self.reports_dir / "evaluation_report.json"
        csv_path = self.reports_dir / "evaluation_results.csv"

        json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            fieldnames = [
                "query_id",
                "query",
                "expected_category",
                "actual_category",
                "expected_complexity",
                "actual_complexity",
                "expected_response_type",
                "predicted_response_type",
                "model_tier",
                "model_id",
                "mode",
                "estimated_cost",
                "actual_cost",
                "overall_match",
            ]
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for result in report["results"]:
                writer.writerow(
                    {
                        "query_id": result["query_id"],
                        "query": result["query"],
                        "expected_category": result["expected"]["category"],
                        "actual_category": result["actual"]["category"],
                        "expected_complexity": result["expected"]["complexity"],
                        "actual_complexity": result["actual"]["complexity"],
                        "expected_response_type": result["expected"]["expected_response_type"],
                        "predicted_response_type": result["actual"]["predicted_response_type"],
                        "model_tier": result["actual"]["model_tier"],
                        "model_id": result["actual"]["model_id"],
                        "mode": result["actual"]["mode"],
                        "estimated_cost": result["actual"]["estimated_cost"],
                        "actual_cost": result["actual"]["actual_cost"],
                        "overall_match": result["matches"]["overall"],
                    }
                )
