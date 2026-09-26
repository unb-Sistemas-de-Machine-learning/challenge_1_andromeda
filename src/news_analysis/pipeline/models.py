from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from news_analysis.pipeline.errors import AnalysisStatus, CriterionStatus


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class ErrorInfo(StrictModel):
    code: str
    message: str
    retryable: bool
    details: dict[str, Any] | None = None


class Article(StrictModel):
    original_url: str
    final_url: str | None = None
    canonical_url: str | None = None
    publisher: str | None = None
    title: str | None = None
    subtitle: str | None = None
    author: str | None = None
    published_at: str | None = None
    content_hash: str
    extracted_character_count: int = Field(ge=0)


class FactCheckReview(StrictModel):
    claim: str | None = None
    publisher_name: str | None = None
    publisher_site: str | None = None
    review_url: str | None = None
    review_title: str | None = None
    review_date: str | None = None
    textual_rating: str | None = None
    language: str | None = None
    applicable: bool
    normalized_value: float | None = Field(default=None, ge=0, le=1)
    raw: dict[str, Any]


class FactCheckCriterionResult(StrictModel):
    available: bool
    status: CriterionStatus
    score: float | None = Field(default=None, ge=0, le=1)
    method: str = "google_fact_check_rating"
    query: str = ""
    reviews_count: int = Field(ge=0)
    applicable_reviews_count: int = Field(ge=0)
    reviews: list[FactCheckReview]
    intended_weight: float = 0.6
    effective_weight: float | None = None
    contribution: float | None = None
    error: ErrorInfo | None = None


class WritingPrediction(StrictModel):
    label: str
    confidence: float = Field(ge=0, le=1)
    writing_score: float = Field(ge=0, le=1)


class WritingSegmentResult(StrictModel):
    index: int = Field(ge=0)
    character_count: int = Field(ge=1)
    token_count: int | None = Field(default=None, ge=1)
    label: str
    confidence: float = Field(ge=0, le=1)
    writing_score: float = Field(ge=0, le=1)


class WritingStyleCriterionResult(StrictModel):
    available: bool
    status: CriterionStatus
    score: float | None = Field(default=None, ge=0, le=1)
    model: str = "vzani/portuguese-fake-news-classifier-bertimbau-combined"
    model_version: str
    prediction: WritingPrediction | None = None
    segments_analyzed: int = Field(ge=0)
    segments: list[WritingSegmentResult]
    qualitative_state: str | None = None
    limitation: str
    intended_weight: float = 0.4
    effective_weight: float | None = None
    contribution: float | None = None
    error: ErrorInfo | None = None


class ReservedCriterionResult(StrictModel):
    available: bool = False
    score: None = None
    status: str = "NOT_IMPLEMENTED"
    planned_model: str = "Ashg2099/xlm-roberta-factchecker"
    planned_flow: list[str]


class CriteriaSet(StrictModel):
    source_credibility: FactCheckCriterionResult
    writing_style: WritingStyleCriterionResult
    factual_claims: ReservedCriterionResult


class FinalScore(StrictModel):
    score: float | None = Field(default=None, ge=0, le=100)
    coverage: float
    intended_weights: dict[str, float]
    effective_weights: dict[str, float]
    formula: str
    limitation: str


class PipelineVersion(StrictModel):
    id: str
    rules_version: str
    fact_check_mapping_version: str
    writing_model_name: str
    writing_model_revision: str | None = None
    dependency_versions: dict[str, str]


class Analysis(StrictModel):
    id: str
    status: AnalysisStatus
    input: dict[str, str]
    article: Article | None = None
    criteria: CriteriaSet
    final: FinalScore
    pipeline_version: PipelineVersion
    limitations: list[str]
    error: ErrorInfo | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


def model_to_dict(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json", exclude_none=True)
    return model.dict(exclude_none=True)
