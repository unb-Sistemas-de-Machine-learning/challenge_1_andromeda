from __future__ import annotations

from news_analysis.pipeline.coverage import calculate_coverage
from news_analysis.pipeline.models import FinalScore

INTENDED_WEIGHTS = {"verifiable_facts": 0.65, "credibility": 0.20, "writing_style": 0.15}
LIMITATION = "A nota é um índice dos critérios avaliados, não uma probabilidade de verdade ou falsidade."


def aggregate_final_score(fact_score: float | None, writing_score: float | None,
                          credibility_score: float | None = None) -> FinalScore:
    available = {
        "verifiable_facts": fact_score is not None,
        "credibility": credibility_score is not None,
        "writing_style": writing_score is not None,
    }
    coverage = calculate_coverage(available, INTENDED_WEIGHTS)
    active_weight_sum = sum(INTENDED_WEIGHTS[key] for key, is_available in available.items() if is_available)

    if active_weight_sum == 0:
        return FinalScore(
            score=None,
            coverage=0,
            intended_weights=INTENDED_WEIGHTS.copy(),
            effective_weights={},
            formula="Nota indisponível: nenhum critério foi avaliado",
            limitation=LIMITATION,
        )

    effective_weights = {
        key: weight / active_weight_sum
        for key, weight in INTENDED_WEIGHTS.items()
        if available[key]
    }
    score = 0.0
    parts: list[str] = []
    if fact_score is not None:
        score += effective_weights["verifiable_facts"] * fact_score * 100
        parts.append(f"{INTENDED_WEIGHTS['verifiable_facts']:.2f} * F")
    if credibility_score is not None:
        score += effective_weights["credibility"] * credibility_score
        parts.append(f"{INTENDED_WEIGHTS['credibility']:.2f} * C")
    if writing_score is not None:
        score += effective_weights["writing_style"] * writing_score * 100
        parts.append(f"{INTENDED_WEIGHTS['writing_style']:.2f} * W")

    numerator = f"({' + '.join(parts)})"
    formula = f"{numerator} * 100" if active_weight_sum == 1 else f"{numerator} / {active_weight_sum:.2f} * 100"

    return FinalScore(
        score=round(score, 4),
        coverage=coverage,
        intended_weights=INTENDED_WEIGHTS.copy(),
        effective_weights=effective_weights,
        formula=formula,
        limitation=LIMITATION,
    )


def contribution(score: float | None, effective_weight: float | None) -> float | None:
    if score is None or effective_weight is None:
        return None
    return round(score * effective_weight * 100, 4)
