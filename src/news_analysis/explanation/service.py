from __future__ import annotations

from news_analysis.config import Settings
from news_analysis.explanation.context import build_explanation_context
from news_analysis.explanation.engine import ExplanationEngine
from news_analysis.explanation.models import SmlExplanation
from news_analysis.explanation.prompt import build_fallback_text
from news_analysis.pipeline.models import Analysis


def build_explanation(
    analysis: Analysis,
    settings: Settings,
    engine: ExplanationEngine | None = None,
) -> SmlExplanation:
    """Build the public summary only from audited criterion states.

    The small local language model can produce fluent-looking but inaccurate
    Portuguese, so its draft is never published as the explanation.
    """
    context = build_explanation_context(analysis)
    return SmlExplanation(
        status="SUCCESS",
        text=build_fallback_text(context),
        context_version=context.context_version,
        validation="FALLBACK",
        evidence_example_publisher=context.fact_check.example_publisher,
        evidence_example_rating=context.fact_check.example_rating,
        evidence_example_url=context.fact_check.example_url,
    )
