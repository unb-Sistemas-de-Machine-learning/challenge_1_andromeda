from __future__ import annotations

from news_analysis.config import Settings
from news_analysis.explanation.context import build_explanation_context
from news_analysis.explanation.engine import ExplanationEngine, FlanT5SmallEngine
from news_analysis.explanation.models import SmlExplanation
from news_analysis.explanation.prompt import build_fallback_text
from news_analysis.explanation.validation import validate_rewrite
from news_analysis.pipeline.models import Analysis


def build_explanation(
    analysis: Analysis,
    settings: Settings,
    engine: ExplanationEngine | None = None,
) -> SmlExplanation:
    """Build an audited summary and optionally apply a checked copy edit."""
    context = build_explanation_context(analysis)
    original = build_fallback_text(context)
    text = original
    validation = 'FALLBACK'
    used_engine = None
    error_code = None
    rewriter = None
    if settings.explanation_sml_enabled:
        try:
            rewriter = engine or FlanT5SmallEngine(
                model_id=settings.explanation_sml_model,
                revision=settings.explanation_sml_revision,
                manifest_path=settings.explanation_sml_manifest,
                max_new_tokens=settings.explanation_max_new_tokens,
                max_input_tokens=settings.explanation_max_input_tokens,
                timeout_seconds=settings.explanation_timeout_seconds,
            )
            candidate = rewriter.rewrite(original)
            accepted, reason = validate_rewrite(original, candidate)
            if accepted:
                text = candidate
                validation = 'VALID'
                used_engine = 'sml'
            else:
                validation = 'REJECTED'
                error_code = reason
        except Exception as exc:
            error_code = type(exc).__name__
    return SmlExplanation(
        status="SUCCESS",
        text=text,
        engine=used_engine,
        model_id=getattr(rewriter, 'model_id', None),
        model_revision=getattr(rewriter, 'model_revision', None),
        prompt_version=getattr(rewriter, 'prompt_version', None),
        artifact_manifest_sha256=getattr(rewriter, 'artifact_manifest_sha256', None),
        context_version=context.context_version,
        validation=validation,
        error_code=error_code,
        evidence_example_publisher=context.fact_check.example_publisher,
        evidence_example_rating=context.fact_check.example_rating,
        evidence_example_url=context.fact_check.example_url,
    )
