from __future__ import annotations

import time

from news_analysis.config import Settings
from news_analysis.explanation.context import build_explanation_context
from news_analysis.explanation.engine import ExplanationEngine, FlanT5SmallEngine
from news_analysis.explanation.validation import validate_explanation
from news_analysis.explanation.models import SmlExplanation
from news_analysis.pipeline.models import Analysis


def build_explanation(
    analysis: Analysis,
    settings: Settings,
    engine: ExplanationEngine | None = None,
):
    """Generate the SML explanation; failures remain explicit and non-authoritative."""
    context_version = "explanation-context-v1"
    if not settings.explanation_sml_enabled:
        return SmlExplanation(status="UNAVAILABLE", engine="sml", context_version=context_version, error_code="sml_disabled")
    context = build_explanation_context(analysis)
    engine = engine or FlanT5SmallEngine(
        cache_dir=settings.model_cache,
        max_new_tokens=settings.explanation_max_new_tokens,
        max_input_tokens=settings.explanation_max_input_tokens,
        model_id=settings.explanation_sml_model,
        revision=settings.explanation_sml_revision,
        manifest_path=settings.explanation_sml_manifest,
        timeout_seconds=settings.explanation_timeout_seconds,
    )
    started = time.perf_counter()
    try:
        # Initialization (including downloads) is not token generation.
        prepare = getattr(engine, "prepare", None)
        if prepare is not None:
            prepare()
        started = time.perf_counter()
        text = engine.generate(context)
        generated_ms = round((time.perf_counter() - started) * 1000)
        if generated_ms > round(settings.explanation_timeout_seconds * 1000):
            return SmlExplanation(status="ERROR", engine="sml", model_id=engine.model_id,
                                  model_revision=engine.model_revision, generated_ms=generated_ms,
                                  tokenizer_revision=getattr(engine, "tokenizer_revision", None),
                                  context_version=context.context_version,
                                  prompt_version=getattr(engine, "prompt_version", None),
                                  artifact_manifest_sha256=getattr(engine, "artifact_manifest_sha256", None),
                                  error_code="sml_timeout")
        valid, reason = validate_explanation(text, context)
        if not valid:
            return SmlExplanation(status="ERROR", engine="sml", model_id=engine.model_id,
                                  model_revision=engine.model_revision, generated_ms=generated_ms,
                                  tokenizer_revision=getattr(engine, "tokenizer_revision", None),
                                  context_version=context.context_version,
                                  prompt_version=getattr(engine, "prompt_version", None),
                                  artifact_manifest_sha256=getattr(engine, "artifact_manifest_sha256", None),
                                  validation="REJECTED",
                                  error_code=f"sml_{reason}")
        return SmlExplanation(status="SUCCESS", text=text, engine="sml", model_id=engine.model_id,
                              model_revision=engine.model_revision, generated_ms=generated_ms,
                              tokenizer_revision=getattr(engine, "tokenizer_revision", None),
                              context_version=context.context_version,
                              prompt_version=getattr(engine, "prompt_version", None),
                              artifact_manifest_sha256=getattr(engine, "artifact_manifest_sha256", None),
                              evidence_example_publisher=context.fact_check.example_publisher,
                              evidence_example_rating=context.fact_check.example_rating,
                              evidence_example_url=context.fact_check.example_url,
                              validation="VALID")
    except TimeoutError:
        return SmlExplanation(status="ERROR", engine="sml", model_id=engine.model_id,
                              model_revision=engine.model_revision,
                              generated_ms=round((time.perf_counter() - started) * 1000),
                              tokenizer_revision=getattr(engine, "tokenizer_revision", None),
                              context_version=context.context_version,
                              prompt_version=getattr(engine, "prompt_version", None),
                              artifact_manifest_sha256=getattr(engine, "artifact_manifest_sha256", None),
                              error_code="sml_timeout")
    except MemoryError:
        return SmlExplanation(status="UNAVAILABLE", engine="sml", model_id=engine.model_id,
                              model_revision=engine.model_revision, error_code="sml_out_of_memory")
    except OSError:
        return SmlExplanation(status="UNAVAILABLE", engine="sml", model_id=engine.model_id,
                              model_revision=engine.model_revision, error_code="sml_artifact_missing")
    except Exception:
        return SmlExplanation(status="ERROR", engine="sml", model_id=engine.model_id,
                              model_revision=engine.model_revision, error_code="sml_unavailable")
