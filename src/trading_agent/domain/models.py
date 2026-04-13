"""Domain value objects used by application services."""
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class IntentDecision:
    """Parsed intent from user input."""

    action: str
    params: Dict[str, Any] = field(default_factory=dict)

