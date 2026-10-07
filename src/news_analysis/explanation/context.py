from __future__ import annotations

import re
from typing import Any

from news_analysis.explanation.models import (
    ExplanationContext,
    FactCheckSummary,
    SourceSummary,
    WritingSummary,
)
from news_analysis.pipeline.models import Analysis


MAX_CLAIM_CHARS = 240
MAX_LIMITATION_CHARS = 180


def _short_text(value: Any, limit: int) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text[:limit] + ("…" if len(text) > limit else "")


def _source_summary(analysis: Analysis) -> SourceSummary:
    source = analysis.criteria.credibility or {}
    flags = [
        *[str(item) for item in source.get("flags", [])],
        *[str(item) for item in source.get("erros", [])],
    ]
    return SourceSummary(
        available=source.get("score_fonte") is not None,
        score=source.get("score_fonte"),
        confidence=_short_text(source.get("confianca_fonte"), 60),
        veto_applied=bool(source.get("veto_dominio_suspeito", False)),
        flags=[item[:120] for item in flags[:3]],
    )


def _confidence_band(score: float | None) -> str:
    if score is None:
        return "indisponível"
    if score > 85:
        return "alta"
    if score > 70:
        return "média"
    if score > 40:
        return "baixa"
    return "baixíssima"


def build_explanation_context(analysis: Analysis) -> ExplanationContext:
    fact = analysis.criteria.verifiable_facts
    writing = analysis.criteria.writing_style
    target_claim = _short_text(fact.target_claim, MAX_CLAIM_CHARS)
    writing_state = _short_text(writing.qualitative_state, 80)
    example = next((review for review in fact.reviews if review.included_in_score and review.review_url), None)
    negative_points = []
    positive_points = []
    unavailable_points = []
    for item in (analysis.criteria.credibility or {}).get("criterios", []):
        name = item.get("nome")
        status = str(item.get("status", "")).lower()
        if name == "veiculo_reconhecido":
            if status == "negativo":
                negative_points.append("o veículo desta notícia não foi encontrado nas bases de veículos consultadas")
            elif status == "indisponivel":
                unavailable_points.append("o veículo desta notícia não pôde ser consultado na base de veículos")
            elif status == "ok":
                evidence = analysis.criteria.credibility_evidence or {}
                origin = "Atlas da Notícia" if any(item.get("source") == "atlas" for item in evidence.get("evidence", [])) else "base de veículos"
                positive_points.append(f"o veículo desta notícia foi encontrado no {origin}" if origin == "Atlas da Notícia" else
                                       "o veículo desta notícia foi encontrado na base de veículos")
        elif name == "tld_institucional":
            if status == "ok":
                domain = str((analysis.criteria.credibility or {}).get("dominio") or "")
                positive_points.append("o site verificado é um site oficial do governo" if domain.endswith(".gov.br")
                                       else "o site verificado possui um domínio institucional oficial")
        elif status == "negativo":
            negative_points.append(str(item.get("detalhe") or name).rstrip("."))
    limitations = [
        item[:MAX_LIMITATION_CHARS]
        for item in analysis.limitations[:3]
        if item
    ]

    # These lists help the future validator detect invented values. They are
    # an audit aid, not a semantic proof of correctness.
    numbers = set(re.findall(r"\d+(?:[.,]\d+)?%?", " ".join([
        str(analysis.final.score) if analysis.final.score is not None else "",
        str(analysis.final.score_before_veto) if analysis.final.score_before_veto is not None else "",
        str(analysis.final.coverage),
        str(fact.reviews_count),
        str(fact.applicable_reviews_count),
        str(fact.publishers_count),
    ])))
    names = [item for item in [target_claim, writing_state] if item]
    return ExplanationContext(
        analysis_id=analysis.id,
        final_score=analysis.final.score,
        confidence_band=_confidence_band(analysis.final.score),
        score_before_veto=analysis.final.score_before_veto,
        source_veto_applied=analysis.final.source_veto_applied,
        coverage=analysis.final.coverage,
        fact_check=FactCheckSummary(
            status=str(fact.status),
            evidence_status=fact.evidence_status,
            target_claim=target_claim,
            reviews_count=fact.reviews_count,
            applicable_reviews_count=fact.applicable_reviews_count,
            publishers_count=fact.publishers_count,
            conflicting_verdicts=fact.conflicting_verdicts,
            example_publisher=example.publisher_name if example else None,
            example_rating=example.textual_rating if example else None,
            example_url=example.review_url if example else None,
        ),
        writing_style=WritingSummary(
            status=str(writing.status),
            available=writing.available,
            score=writing.score,
            qualitative_state=writing_state,
        ),
        source=_source_summary(analysis),
        negative_source_points=negative_points[:4],
        positive_source_points=positive_points[:4],
        unavailable_source_points=unavailable_points[:4],
        writing_issue=writing_state if writing_state and writing_state.lower() not in {"nenhum", "indisponível"} else None,
        limitations=limitations,
        allowed_numbers=sorted(numbers),
        allowed_names=names,
    )
