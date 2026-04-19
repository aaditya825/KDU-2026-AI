"""Shared typed models for the FixIt LLMOps scaffold."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class QueryInput(BaseModel):
    query: str = Field(..., min_length=1)
    query_id: str
    timestamp: datetime


class ClassificationResult(BaseModel):
    category: str
    complexity: Literal["low", "medium", "high"]
    expected_response_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    source: str = "rule-based"
    model_id: str | None = None
    fallback_reason: str | None = None
    usage_details: dict[str, Any] = Field(default_factory=dict)


class RoutingDecision(BaseModel):
    model_tier: str
    model_id: str
    prompt_key: str
    prompt_version: int
    estimated_cost: float = Field(ge=0.0)


class PromptRuntimeMetadata(BaseModel):
    usage_count: int = Field(default=0, ge=0)
    success_count: int = Field(default=0, ge=0)
    failure_count: int = Field(default=0, ge=0)
    last_used_at: str | None = None
    average_cost_usd: float | None = Field(default=None, ge=0.0)
    average_latency_ms: float | None = Field(default=None, ge=0.0)
    evaluation_score: float | None = Field(default=None, ge=0.0, le=1.0)


class PromptVersion(BaseModel):
    key: str
    version: int
    template: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    runtime_metadata: PromptRuntimeMetadata = Field(default_factory=PromptRuntimeMetadata)


class CostUsageRecord(BaseModel):
    query_id: str
    model_id: str
    estimated_cost: float = Field(ge=0.0)
    actual_cost: float = Field(ge=0.0)
    usage_details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


class GenerationResult(BaseModel):
    model_id: str
    provider: str
    text: str
    usage_details: dict[str, Any] = Field(default_factory=dict)


class BudgetCheckResult(BaseModel):
    mode: Literal["normal", "warning", "critical", "degraded"]
    reason: str | None = None
    projected_daily_total: float = Field(ge=0.0)
    projected_monthly_total: float = Field(ge=0.0)


class QueryResponse(BaseModel):
    query_id: str
    category: str
    complexity: Literal["low", "medium", "high"]
    response_text: str
    model_id: str
    model_tier: str
    prompt_key: str
    prompt_version: int
    estimated_cost: float = Field(ge=0.0)
    actual_cost: float = Field(ge=0.0)
    mode: Literal["normal", "warning", "critical", "degraded"]
    metadata: dict[str, Any] = Field(default_factory=dict)


class AppSettings(BaseModel):
    name: str
    environment: str
    entry_mode: str


class FeatureFlags(BaseModel):
    use_rule_based_classifier: bool = True
    enable_prompt_versioning: bool = True
    enforce_strict_budget: bool = True
    include_debug_metadata: bool = True


class ClassifierConfig(BaseModel):
    mode: Literal["rule_based", "gemini", "hybrid"] = "rule_based"
    provider: str = "gemini"
    model_id: str
    low_confidence_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    fallback_to_rule_based_on_error: bool = True


class CostLimits(BaseModel):
    daily_usd: float = Field(gt=0.0)
    monthly_usd: float = Field(gt=0.0)
    warning_threshold_ratio: float = Field(ge=0.0, le=1.0)
    critical_threshold_ratio: float = Field(ge=0.0, le=1.0)


class ModelTierConfig(BaseModel):
    provider: str
    model_id: str
    max_input_tokens: int = Field(gt=0)
    max_output_tokens: int = Field(gt=0)


class ModelsConfig(BaseModel):
    default_tier: str
    tiers: dict[str, ModelTierConfig]


class RoutingRule(BaseModel):
    name: str
    category: str
    complexity: Literal["low", "medium", "high"]
    route_to_tier: str
    prompt_key: str
    prompt_version: int = Field(gt=0)


class RoutingConfig(BaseModel):
    default_prompt_key: str
    default_prompt_version: int = Field(gt=0)
    rules: list[RoutingRule]
    low_confidence_fallback_tier: str


class PromptsConfig(BaseModel):
    defaults: dict[str, int]


class ActiveConfig(BaseModel):
    app: AppSettings
    feature_flags: FeatureFlags
    classifier: ClassifierConfig
    cost_limits: CostLimits
    models: ModelsConfig
    routing: RoutingConfig
    prompts: PromptsConfig


class ModelPricing(BaseModel):
    input_cost_per_1k_tokens_usd: float = Field(ge=0.0)
    output_cost_per_1k_tokens_usd: float = Field(ge=0.0)


class ProviderPricing(BaseModel):
    models: dict[str, ModelPricing]


class PricingConfig(BaseModel):
    providers: dict[str, ProviderPricing]
