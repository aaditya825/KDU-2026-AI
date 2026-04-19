"""Reusable rule-based classification helpers."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.models import ClassificationResult


@dataclass(frozen=True)
class RuleMatchDetails:
    """Internal rule matching summary for classifier orchestration."""

    result: ClassificationResult
    matched_categories: tuple[str, ...]

    @property
    def is_ambiguous(self) -> bool:
        return len(self.matched_categories) > 1


def classify_with_rules(query: str) -> RuleMatchDetails:
    """Classify a query using deterministic keyword matching."""
    normalized = query.strip().lower()

    complaint_keywords = {
        "refund",
        "complaint",
        "damaged",
        "terrible",
        "compensation",
        "didn't show",
        "did not show",
        "no one replied",
    }
    booking_keywords = {
        "book",
        "booking",
        "appointment",
        "reschedule",
        "schedule",
        "cancel",
        "move my booking",
    }
    faq_keywords = {
        "hours",
        "open",
        "service",
        "location",
        "do you",
        "can you",
    }

    matched_categories: list[str] = []
    if any(keyword in normalized for keyword in complaint_keywords):
        matched_categories.append("complaint")
    if any(keyword in normalized for keyword in booking_keywords):
        matched_categories.append("booking")
    if any(keyword in normalized for keyword in faq_keywords) or "?" in normalized:
        matched_categories.append("FAQ")

    if "complaint" in matched_categories:
        result = ClassificationResult(
            category="complaint",
            complexity="high",
            expected_response_type="complex",
            confidence=0.92,
            source="rule-based",
        )
    elif "booking" in matched_categories:
        confidence = 0.88
        if "not sure" in normalized or "help" in normalized:
            confidence = 0.60

        result = ClassificationResult(
            category="booking",
            complexity="medium",
            expected_response_type="standard",
            confidence=confidence,
            source="rule-based",
        )
    elif "FAQ" in matched_categories:
        result = ClassificationResult(
            category="FAQ",
            complexity="low",
            expected_response_type="simple",
            confidence=0.85,
            source="rule-based",
        )
    else:
        result = ClassificationResult(
            category="FAQ",
            complexity="medium",
            expected_response_type="standard",
            confidence=0.50,
            source="rule-based",
        )

    return RuleMatchDetails(result=result, matched_categories=tuple(matched_categories))
