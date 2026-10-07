from __future__ import annotations

from news_analysis.explanation.models import ExplanationContext


_FACT_STATES = {
    "SUPPORTED": "Há evidências favoráveis ao fato analisado.",
    "REFUTED": "Há evidências contrárias ao fato analisado.",
    "MIXED": "Há evidências divergentes sobre o fato analisado.",
    "MATCHED_UNSCORED": "Há fontes relacionadas, mas faltam dados para concluir.",
    "UNAVAILABLE": "Faltam evidências factuais para concluir.",
}


def build_prompt(context: ExplanationContext, *, include_details: bool = True) -> str:
    """Summarize the results, not the article; optional detail can be omitted.

    The engine checks the token budget before generation so essential facts
    are never silently truncated away.
    """
    factual = _FACT_STATES.get(context.fact_check.evidence_status, _FACT_STATES["UNAVAILABLE"])
    if context.source_veto_applied:
        source = "veto aplicado à fonte"
    elif context.negative_source_points:
        source = "Pontos negativos encontrados"
        if include_details:
            source += ": " + context.negative_source_points[0]
    elif context.unavailable_source_points:
        source = context.unavailable_source_points[0] if include_details else "reconhecimento do veículo indisponível"
    elif not context.source.available:
        source = "dados indisponíveis"
    else:
        source = "sem problemas informados"
    positive = "; ponto positivo: " + context.positive_source_points[0] if context.positive_source_points else ""
    if not context.writing_style.available:
        writing = "dados indisponíveis"
    elif context.writing_issue:
        writing = (" ".join(context.writing_issue.replace("_", " ").split())[:60]
                   if include_details else "há sinais de problemas")
    else:
        writing = "sem problemas informados"
    return (
        "Resuma em português em até três frases completas. Não inclua nota numérica nem nomes internos de critérios. Use apenas estes dados:\n"
        f"Confiabilidade {context.confidence_band}. "
        f"{factual} Fonte: {source}{positive}; escrita: {writing}; "
        f"cobertura {'parcial' if context.coverage < 100 else 'completa'}."
    )


def build_fallback_text(context: ExplanationContext) -> str:
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
