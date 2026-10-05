from __future__ import annotations

from news_analysis.pipeline.coverage import calculate_coverage
from news_analysis.pipeline.models import FinalScore

INTENDED_WEIGHTS = {"verifiable_facts": 0.5, "writing_style": 0.3, "source_credibility": 0.2}
LIMITATION = "Final score is an operational index from executed criteria, not a probability of truth or falsity."


def aggregate_final_score(
    fact_score: float | None,
    writing_score: float | None,
    credibility_score: float | None,
) -> FinalScore:
    available = {
        "verifiable_facts": fact_score is not None,
        "writing_style": writing_score is not None,
        "source_credibility": credibility_score is not None,
    }
    coverage = calculate_coverage(available, INTENDED_WEIGHTS)
    active_weight_sum = sum(INTENDED_WEIGHTS[key] for key, is_available in available.items() if is_available)

    if active_weight_sum == 0:
        return FinalScore(
            score=None,
            coverage=0,
            intended_weights=INTENDED_WEIGHTS.copy(),
            effective_weights={},
            formula="score = null because no current criteria are available",
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
        parts.append(f"{effective_weights['verifiable_facts']:.2f} * F")
    if writing_score is not None:
        score += effective_weights["writing_style"] * writing_score * 100
        parts.append(f"{effective_weights['writing_style']:.2f} * W")
    if credibility_score is not None:
        score += effective_weights["source_credibility"] * credibility_score * 100
        parts.append(f"{effective_weights['source_credibility']:.2f} * C")

    return FinalScore(
        score=round(score, 4),
        coverage=coverage,
        intended_weights=INTENDED_WEIGHTS.copy(),
        effective_weights=effective_weights,
        formula=f"({ ' + '.join(parts) }) * 100",
        limitation=LIMITATION,
    )


def contribution(score: float | None, effective_weight: float | None) -> float | None:
    if score is None or effective_weight is None:
        return None
    return round(score * effective_weight * 100, 4)
