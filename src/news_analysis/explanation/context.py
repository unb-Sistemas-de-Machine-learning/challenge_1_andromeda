from __future__ import annotations

from news_analysis.explanation.models import (
    ExplanationContext,
    FactCheckSummary,
    SourceSummary,
    WritingSummary,
)
from news_analysis.pipeline.models import Analysis


def _source_summary(analysis: Analysis) -> SourceSummary:
    source = analysis.criteria.credibility or {}
    return SourceSummary(available=source.get("score_fonte") is not None)


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
    writing_state = writing.qualitative_state
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
    return ExplanationContext(
        confidence_band=_confidence_band(analysis.final.score),
        coverage=analysis.final.coverage,
        fact_check=FactCheckSummary(
            evidence_status=fact.evidence_status,
            example_publisher=example.publisher_name if example else None,
            example_rating=example.textual_rating if example else None,
            example_url=example.review_url if example else None,
        ),
        writing_style=WritingSummary(
            available=writing.available,
        ),
        source=_source_summary(analysis),
        negative_source_points=negative_points[:4],
        positive_source_points=positive_points[:4],
        unavailable_source_points=unavailable_points[:4],
        writing_issue=writing_state if writing_state and writing_state.lower() not in {"nenhum", "indisponível"} else None,
    )
