"""Configurable query classifier implementations."""

from __future__ import annotations

from src.classifier.rules import RuleMatchDetails, classify_with_rules
from src.core.models import ActiveConfig, ClassificationResult
from src.llm_client.client import LLMClient


class QueryClassifier:
    """Classifies incoming support queries using rule-based, Gemini, or hybrid mode."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient(provider_mode="mock")

    def classify(
        self,
        query: str,
        active_config: ActiveConfig | None = None,
    ) -> ClassificationResult:
        """Return classification details for a query."""
        rule_match = classify_with_rules(query)
        if active_config is None:
            return rule_match.result

        classifier_config = active_config.classifier
        if classifier_config.mode == "rule_based":
            return rule_match.result

        if classifier_config.provider != "gemini":
            return self._handle_classifier_error(
                rule_match=rule_match,
                reason=(
                    "classifier provider "
                    f"{classifier_config.provider} is not supported; using rule-based fallback"
                ),
                allow_fallback=classifier_config.fallback_to_rule_based_on_error,
            )

        if classifier_config.mode == "hybrid" and not self._should_use_gemini(
            rule_match,
            classifier_config.low_confidence_threshold,
        ):
            return rule_match.result

        try:
            return self.llm_client.classify_query(
                query=query,
                model_id=classifier_config.model_id,
                confidence_threshold=classifier_config.low_confidence_threshold,
            )
        except RuntimeError as exc:
            return self._handle_classifier_error(
                rule_match=rule_match,
                reason=f"Gemini classification failed: {exc}",
                allow_fallback=classifier_config.fallback_to_rule_based_on_error,
            )

    @staticmethod
    def _should_use_gemini(
        rule_match: RuleMatchDetails,
        low_confidence_threshold: float,
    ) -> bool:
        return rule_match.is_ambiguous or rule_match.result.confidence < low_confidence_threshold

    @staticmethod
    def _handle_classifier_error(
        *,
        rule_match: RuleMatchDetails,
        reason: str,
        allow_fallback: bool,
    ) -> ClassificationResult:
        if not allow_fallback:
            raise RuntimeError(reason)

        return rule_match.result.model_copy(
            update={
                "fallback_reason": reason,
            }
        )
