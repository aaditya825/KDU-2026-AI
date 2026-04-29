from __future__ import annotations

import importlib.util

from app.adapters.llm_adapter import LocalFallbackAdapter, build_llm_adapter


def test_build_llm_adapter_falls_back_when_provider_package_missing(monkeypatch):
    real_find_spec = importlib.util.find_spec

    def fake_find_spec(name: str):
        if name == "google.genai":
            return None
        return real_find_spec(name)

    monkeypatch.setattr("app.adapters.llm_adapter.importlib.util.find_spec", fake_find_spec)

    adapter = build_llm_adapter(
        provider="gemini",
        model="gemini-2.5-flash-lite",
        api_keys={"gemini": "dummy-key", "openai": ""},
    )
    assert isinstance(adapter, LocalFallbackAdapter)
