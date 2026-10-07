from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExplanationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class FactCheckSummary(ExplanationModel):
    status: str
    evidence_status: str | None = None
    target_claim: str | None = None
    reviews_count: int = Field(ge=0)
    applicable_reviews_count: int = Field(ge=0)
    publishers_count: int = Field(ge=0)
    conflicting_verdicts: bool = False
    example_publisher: str | None = None
    example_rating: str | None = None
    example_url: str | None = None


class WritingSummary(ExplanationModel):
    status: str
    available: bool
    score: float | None = Field(default=None, ge=0, le=1)
    qualitative_state: str | None = None


class SourceSummary(ExplanationModel):
    available: bool
    score: float | None = Field(default=None, ge=0, le=100)
    confidence: str | None = None
    veto_applied: bool = False
    flags: list[str] = Field(default_factory=list)


class ExplanationContext(ExplanationModel):
    context_version: str = "explanation-context-v1"
    analysis_id: str
    language: Literal["pt-BR"] = "pt-BR"
    final_score: float | None = Field(default=None, ge=0, le=100)
    confidence_band: str
    score_before_veto: float | None = Field(default=None, ge=0, le=100)
    source_veto_applied: bool | None = None
    coverage: float = Field(ge=0, le=100)
    fact_check: FactCheckSummary
    writing_style: WritingSummary
    source: SourceSummary
    negative_source_points: list[str] = Field(default_factory=list)
    positive_source_points: list[str] = Field(default_factory=list)
    unavailable_source_points: list[str] = Field(default_factory=list)
    writing_issue: str | None = None
    limitations: list[str] = Field(default_factory=list)
    allowed_numbers: list[str] = Field(default_factory=list)
    allowed_names: list[str] = Field(default_factory=list)


class SmlExplanation(ExplanationModel):
    status: Literal["IDLE", "LOADING", "SUCCESS", "ERROR", "UNAVAILABLE"]
    text: str | None = None
    engine: Literal["sml"] | None = None
    model_id: str | None = None
    model_revision: str | None = None
    tokenizer_revision: str | None = None
    context_version: str | None = None
    prompt_version: str | None = None
    artifact_manifest_sha256: str | None = None
    evidence_example_publisher: str | None = None
    evidence_example_rating: str | None = None
    evidence_example_url: str | None = None
    validation: Literal["VALID", "REJECTED", "FALLBACK"] | None = None
    generated_ms: int | None = Field(default=None, ge=0)
    error_code: str | None = None
