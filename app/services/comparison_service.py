"""
app/services/comparison_service.py
----------------------------------
Model comparison service.

Runs each configured model on summary, key-points, and topic-tag stages and
records latency, estimated cost, quality notes, and failures.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

from app.config.model_registry import GENERATION_MAX_TOKENS, LLM_PROVIDER_MODELS
from app.models.domain import ComparisonReport
from app.utils.logging_utils import get_logger

log = get_logger(__name__)

_COST_PER_1K_TOKENS: dict[str, float] = {
    "gemini": 0.0004,
    "openai": 0.004,
    "local": 0.0,
}

_STAGE_PROMPTS: dict[str, str] = {
    "summary": (
        "Summarize the following content in about 150 words. "
        "Keep the meaning accurate and avoid unsupported claims.\n\nContent:\n{content}"
    ),
    "key_points": (
        "Extract 5-7 key points from the following content. "
        "Return only a numbered list.\n\nContent:\n{content}"
    ),
    "topic_tags": (
        "Generate 5-10 short topic tags for the following content. "
        "Return only a comma-separated list.\n\nContent:\n{content}"
    ),
}


@dataclass
class _ModelConfig:
    provider: str
    model_name: str
    api_key: str


def _estimate_cost(provider: str, output_text: str) -> float:
    tokens = len(output_text.split()) * 1.3
    return _COST_PER_1K_TOKENS.get(provider, 0.0) * tokens / 1000


def _quality_notes(stage: str, output_text: str, status: str) -> str:
    if status != "success":
        return "No quality score - run failed."
    text = output_text.strip()
    if not text:
        return "Empty output."
    if "local fallback" in text.lower():
        return "Fallback output only; low quality confidence."
    if stage == "summary":
        words = len(text.split())
        if 80 <= words <= 220:
            return "Reasonable summary length and structure."
        return "Summary length outside target range."
    if stage == "key_points":
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if 3 <= len(lines) <= 10:
            return "Key-point formatting looks plausible."
        return "Key-point formatting may be weak."
    if stage == "topic_tags":
        tags = [t.strip() for t in text.split(",") if t.strip()]
        if 3 <= len(tags) <= 12:
            return "Tag density looks reasonable."
        return "Tag output size outside expected range."
    return "Output captured."


class ComparisonService:
    """Compare multiple LLM configurations on identical processed content."""

    def __init__(self, configs: list[_ModelConfig]) -> None:
        self._configs = configs

    def compare(self, file_id: str, cleaned_text: str) -> ComparisonReport:
        truncated = cleaned_text[:4000]
        model_results: list[dict[str, Any]] = []

        for cfg in self._configs:
            for stage, prompt_tmpl in _STAGE_PROMPTS.items():
                result = self._run_one(
                    file_id=file_id,
                    text=truncated,
                    cfg=cfg,
                    stage=stage,
                    prompt_tmpl=prompt_tmpl,
                )
                model_results.append(result)

        summary = self._build_summary(model_results)
        observations = self._observations(model_results)
        return ComparisonReport(
            file_id=file_id,
            model_results=model_results,
            metric_summary=summary,
            observations=observations,
        )

    def _run_one(
        self,
        file_id: str,
        text: str,
        cfg: _ModelConfig,
        stage: str,
        prompt_tmpl: str,
    ) -> dict[str, Any]:
        from app.adapters.llm_adapter import (
            GeminiAdapter,
            LocalFallbackAdapter,
            OpenAIAdapter,
        )

        adapter_map = {
            "gemini": lambda: GeminiAdapter(api_key=cfg.api_key, model=cfg.model_name),
            "openai": lambda: OpenAIAdapter(api_key=cfg.api_key, model=cfg.model_name),
            "local": lambda: LocalFallbackAdapter(),
        }
        build_fn = adapter_map.get(cfg.provider, adapter_map["local"])

        try:
            adapter = build_fn()
        except Exception as exc:
            return {
                "stage": stage,
                "provider": cfg.provider,
                "model_name": cfg.model_name,
                "status": "failed",
                "error_message": f"Adapter init failed: {exc}",
                "latency_ms": 0,
                "estimated_cost": 0.0,
                "quality_notes": "No quality score - adapter initialization failed.",
                "output_preview": "",
            }

        prompt = prompt_tmpl.format(content=text)
        t0 = time.monotonic()
        try:
            output = adapter.generate(
                prompt,
                max_tokens=GENERATION_MAX_TOKENS["comparison"],
            )
            status = "success"
            error_msg = ""
        except Exception as exc:
            log.warning("Comparison run failed for %s/%s (%s): %s", cfg.provider, cfg.model_name, stage, exc)
            output = ""
            status = "failed"
            error_msg = str(exc)

        latency = int((time.monotonic() - t0) * 1000)
        cost = _estimate_cost(cfg.provider, output)
        quality_notes = _quality_notes(stage, output, status)

        log.info(
            "Comparison run complete",
            extra={
                "file_id": file_id,
                "provider": cfg.provider,
                "model": cfg.model_name,
                "stage": stage,
                "latency_ms": latency,
                "status": status,
            },
        )
        return {
            "stage": stage,
            "provider": cfg.provider,
            "model_name": cfg.model_name,
            "status": status,
            "error_message": error_msg,
            "latency_ms": latency,
            "estimated_cost": cost,
            "quality_notes": quality_notes,
            "output_preview": output[:300],
        }

    @staticmethod
    def _build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
        successful = [r for r in results if r["status"] == "success"]
        if not successful:
            return {"fastest_ms": "N/A", "cheapest": "N/A", "success_rate": f"0/{len(results)}"}

        fastest = min(successful, key=lambda r: r["latency_ms"])
        cheapest = min(successful, key=lambda r: r["estimated_cost"])
        stage_stats: dict[str, dict[str, Any]] = {}
        for stage in _STAGE_PROMPTS:
            stage_success = [r for r in successful if r["stage"] == stage]
            if stage_success:
                stage_stats[stage] = {
                    "avg_latency_ms": int(sum(r["latency_ms"] for r in stage_success) / len(stage_success)),
                    "runs": len(stage_success),
                }
        return {
            "fastest_ms": fastest["latency_ms"],
            "fastest_model": f"{fastest['provider']}/{fastest['model_name']} ({fastest['stage']})",
            "cheapest_cost_usd": cheapest["estimated_cost"],
            "cheapest_model": f"{cheapest['provider']}/{cheapest['model_name']} ({cheapest['stage']})",
            "success_rate": f"{len(successful)}/{len(results)}",
            "stage_stats": stage_stats,
        }

    @staticmethod
    def _observations(results: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        for r in results:
            prefix = f"{r['provider']}/{r['model_name']}[{r['stage']}]"
            if r["status"] == "success":
                lines.append(
                    f"{prefix}: {r['latency_ms']} ms, ${r['estimated_cost']:.5f}, {r['quality_notes']}"
                )
            else:
                lines.append(f"{prefix}: FAILED - {r.get('error_message', '')}")
        return " | ".join(lines)


def build_comparison_configs(
    gemini_key: str,
    openai_key: str,
) -> list[_ModelConfig]:
    """Build default comparison configurations."""
    configs: list[_ModelConfig] = []

    if gemini_key:
        configs.append(
            _ModelConfig(
                provider="gemini",
                model_name=LLM_PROVIDER_MODELS["gemini"],
                api_key=gemini_key,
            )
        )
    if openai_key:
        configs.append(
            _ModelConfig(
                provider="openai",
                model_name=LLM_PROVIDER_MODELS["openai"],
                api_key=openai_key,
            )
        )

    configs.append(
        _ModelConfig(
            provider="local",
            model_name=LLM_PROVIDER_MODELS["local"],
            api_key="",
        )
    )
    return configs
