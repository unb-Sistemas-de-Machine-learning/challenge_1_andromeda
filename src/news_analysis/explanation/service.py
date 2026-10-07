from __future__ import annotations

from news_analysis.config import Settings
from news_analysis.explanation.context import build_explanation_context
from news_analysis.explanation.models import ExplanationResult
from news_analysis.explanation.summary import build_explanation_text
from news_analysis.pipeline.models import Analysis


def build_explanation(
    analysis: Analysis,
    settings: Settings,
) -> ExplanationResult:
    """Build an auditable summary directly from criterion states."""
    context = build_explanation_context(analysis)
    return ExplanationResult(
        status="SUCCESS",
        text=build_explanation_text(context),
        context_version=context.context_version,
        evidence_example_publisher=context.fact_check.example_publisher,
        evidence_example_rating=context.fact_check.example_rating,
        evidence_example_url=context.fact_check.example_url,
    )
