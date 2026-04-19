"""Prompt manager implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.core.models import PromptVersion
from src.prompt_manager.metadata_tracker import PromptMetadataTracker


class PromptManager:
    """Loads and resolves versioned prompts."""

    def __init__(
        self,
        prompts_root: Path,
        metadata_tracker: PromptMetadataTracker | None = None,
    ) -> None:
        self.prompts_root = prompts_root
        self.metadata_tracker = metadata_tracker

    def load(self, prompt_key: str, prompt_version: int) -> PromptVersion:
        """Load a prompt by key and version."""
        prompt_path = self.prompts_root / prompt_key / f"v{prompt_version}.yaml"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        with prompt_path.open("r", encoding="utf-8") as handle:
            raw_prompt = yaml.safe_load(handle)

        if not isinstance(raw_prompt, dict):
            raise ValueError(f"Prompt file must contain a mapping: {prompt_path}")

        return self._enrich_prompt(PromptVersion.model_validate(raw_prompt))

    def load_with_fallback(
        self,
        prompt_key: str,
        prompt_version: int,
        *,
        fallback_key: str,
        fallback_version: int,
    ) -> tuple[PromptVersion, str | None]:
        """Load a prompt and fall back to base/default assets if needed."""
        try:
            return self.load(prompt_key, prompt_version), None
        except (FileNotFoundError, ValueError):
            if prompt_key == fallback_key and prompt_version == fallback_version:
                return self._builtin_fallback_prompt(), "requested prompt missing; using built-in fallback prompt"

        try:
            return (
                self.load(fallback_key, fallback_version),
                f"requested prompt {prompt_key}:v{prompt_version} unavailable; using fallback prompt {fallback_key}:v{fallback_version}",
            )
        except (FileNotFoundError, ValueError):
            return self._builtin_fallback_prompt(), "configured fallback prompt unavailable; using built-in fallback prompt"

    def render(self, prompt: PromptVersion, variables: dict[str, Any]) -> str:
        """Render a prompt template using simple placeholder substitution."""
        rendered = prompt.template
        for key, value in variables.items():
            rendered = rendered.replace(f"{{{{ {key} }}}}", str(value))

        return rendered

    def _enrich_prompt(self, prompt: PromptVersion) -> PromptVersion:
        if self.metadata_tracker is not None:
            prompt.runtime_metadata = self.metadata_tracker.get_runtime_metadata(
                prompt.key,
                prompt.version,
            )
        return prompt

    def _builtin_fallback_prompt(self) -> PromptVersion:
        return self._enrich_prompt(
            PromptVersion(
                key="base",
                version=0,
                template=(
                    "You are supporting customers for FixIt, a home services marketplace.\n"
                    "Provide a brief, helpful response based on the customer query.\n\n"
                    "Customer query:\n"
                    "{{ query }}\n"
                ),
                metadata={
                    "owner": "system",
                    "notes": "Built-in fallback prompt used when prompt assets are unavailable.",
                },
            )
        )
