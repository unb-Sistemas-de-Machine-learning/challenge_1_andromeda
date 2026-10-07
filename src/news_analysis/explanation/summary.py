from __future__ import annotations

from news_analysis.explanation.models import ExplanationContext


_FACT_STATES = {
    "SUPPORTED": "Há evidências favoráveis ao fato analisado.",
    "REFUTED": "Há evidências contrárias ao fato analisado.",
    "MIXED": "Há evidências divergentes sobre o fato analisado.",
    "MATCHED_UNSCORED": "Há fontes relacionadas, mas faltam dados para concluir.",
    "UNAVAILABLE": "Faltam evidências factuais para concluir.",
}


def build_explanation_text(context: ExplanationContext) -> str:
    """Complete, auditable public summary based on criterion states."""
    factual = _FACT_STATES.get(context.fact_check.evidence_status, _FACT_STATES["UNAVAILABLE"])
    details = []
    if context.coverage < 100:
        if context.fact_check.evidence_status == "UNAVAILABLE" and context.writing_style.available and context.source.available:
            factual = "Não há checagem factual disponível. A avaliação considera a credibilidade da fonte e o estilo de escrita; não confirma os fatos da notícia."
        elif context.fact_check.evidence_status == "UNAVAILABLE" and context.writing_style.available:
            factual = "Não há checagem factual disponível. A avaliação considera apenas o estilo de escrita e não confirma os fatos da notícia."
        elif context.fact_check.evidence_status == "UNAVAILABLE" and context.source.available:
            factual = "Não há checagem factual disponível. A avaliação considera apenas a credibilidade da fonte e não confirma os fatos da notícia."
        else:
            factual += " A avaliação é parcial."
    if context.negative_source_points:
        details.append("Pontos negativos encontrados: " + "; ".join(context.negative_source_points) + ".")
    if context.positive_source_points:
        details.append("Pontos positivos encontrados: " + "; ".join(context.positive_source_points) + ".")
    if context.unavailable_source_points:
        details.append("Sobre a fonte, " + "; ".join(context.unavailable_source_points) + ".")
    if not context.source.available and not details:
        details.append("Dados sobre a fonte indisponíveis.")
    if not context.writing_style.available:
        details.append("Análise da escrita indisponível.")
    elif context.writing_issue:
        details.append("A escrita apresentou sinais que exigem atenção.")
    return " ".join([f"Confiabilidade {context.confidence_band}.", factual, *details])
