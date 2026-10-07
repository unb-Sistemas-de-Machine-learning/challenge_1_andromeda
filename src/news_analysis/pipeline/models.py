from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_serializer

from news_analysis.explanation.models import ExplanationResult
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
    claimant: str | None = None
    claim_date: str | None = None
    applicable: bool
    included_in_score: bool = False
    exclusion_reason: str | None = None
    publisher_key: str | None = None
    normalized_value: float | None = Field(default=None, ge=0, le=1)
    match_classification: Literal['SAME_CLAIM', 'RELATED', 'DIFFERENT'] | None = None
    match_similarity: float | None = Field(default=None, ge=0, le=1)
    match_reason: str | None = None
    matcher_version: str | None = None
    normalized_target: str | None = None
    normalized_claim: str | None = None
    rating_interpretation: Literal['CONTEXT', 'CLAIM_VERDICT', 'UNMAPPED'] | None = None
    raw: dict[str, Any]


class FactCheckEvidence(StrictModel):
    available: bool
    status: CriterionStatus
    score: float | None = Field(default=None, ge=0, le=1)
    name: str = "Checagem de fatos verificáveis"
    method: str = "google_fact_check_claim_reviews"
    target_claim: str | None = None
    claim_origin: str = "article_title_or_excerpt"
    scope: str = "Uma afirmação selecionada; não verifica todos os fatos da notícia nem a reputação da fonte."
    formula: str = "F = mean(publisher means of unique applicable mapped reviews)"
    limitation: str = "Google retrieves published reviews; matching is lexical, the score is project-defined, and absence of a review is not a verdict."
    scored_reviews_count: int = 0
    publishers_count: int = 0
    publisher_scores: dict[str, float] = Field(default_factory=dict)
    conflicting_verdicts: bool = False
    search_attempts: list[dict[str, Any]] = Field(default_factory=list)
    search_truncated: bool = False
    search_incomplete: bool = False
    evidence_status: Literal['SUPPORTED', 'REFUTED', 'MIXED', 'MATCHED_UNSCORED', 'UNAVAILABLE'] | None = None
    query: str = ""
    reviews_count: int = Field(ge=0)
    applicable_reviews_count: int = Field(ge=0)
    related_reviews_count: int = Field(default=0, ge=0)
    reviews: list[FactCheckReview]
    error: ErrorInfo | None = None


class FactCheckCriterionResult(FactCheckEvidence):
    additional_claims: list[FactCheckEvidence] = Field(default_factory=list)
    intended_weight: float = 0.65
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
    intended_weight: float = 0.15
    effective_weight: float | None = None
    contribution: float | None = None
    error: ErrorInfo | None = None


class HistoricalSourceSignal(StrictModel):
    key: str
    label: str
    passed: bool
    weight: float = Field(ge=0, le=1)
    evidence: str


class HistoricalSourceCredibility(StrictModel):
    """Read-only compatibility with the v4 metadata criterion (50/30/20)."""
    available: bool
    status: CriterionStatus
    score: float | None = Field(default=None, ge=0, le=1)
    name: str | None = None
    method: str | None = None
    scope: str | None = None
    formula: str | None = None
    limitation: str | None = None
    signals: list[HistoricalSourceSignal]
    intended_weight: float
    effective_weight: float | None = None
    contribution: float | None = None


class CriteriaSet(StrictModel):
    verifiable_facts: FactCheckCriterionResult
    writing_style: WritingStyleCriterionResult
    credibility: dict[str, Any] | None = None
    credibility_evidence: dict[str, Any] | None = None
    source_credibility: HistoricalSourceCredibility | None = Field(
        default=None, description="Historical v4 metadata criterion only; never produced by new analyses.")

    @model_serializer(mode='wrap')
    def omit_absent_historical_criterion(self, handler):
        result = handler(self)
        if self.source_credibility is None:
            result.pop('source_credibility', None)
        return result


class FinalScore(StrictModel):
    score: float | None = Field(default=None, ge=0, le=100)
    score_before_veto: float | None = Field(default=None, ge=0, le=100)
    source_veto_applied: bool | None = None
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
    credibility_policy_hash: str | None = None


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
    explanation: ExplanationResult | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


def model_to_dict(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json", exclude_none=True)
    return model.dict(exclude_none=True)
