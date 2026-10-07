from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ExplanationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class FactCheckSummary(ExplanationModel):
    evidence_status: str | None = None
    example_publisher: str | None = None
    example_rating: str | None = None
    example_url: str | None = None


class WritingSummary(ExplanationModel):
    available: bool


class SourceSummary(ExplanationModel):
    available: bool


class ExplanationContext(ExplanationModel):
    context_version: str = "explanation-context-v1"
    confidence_band: str
    coverage: float
    fact_check: FactCheckSummary
    writing_style: WritingSummary
    source: SourceSummary
    negative_source_points: list[str]
    positive_source_points: list[str]
    unavailable_source_points: list[str]
    writing_issue: str | None = None


class ExplanationResult(ExplanationModel):
    status: Literal["SUCCESS", "ERROR", "UNAVAILABLE"]
    text: str | None = None
    context_version: str | None = None
    evidence_example_publisher: str | None = None
    evidence_example_rating: str | None = None
    evidence_example_url: str | None = None
