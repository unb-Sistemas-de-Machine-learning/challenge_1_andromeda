from __future__ import annotations

from news_analysis.pipeline.models import ReservedCriterionResult


def reserved_factual_claims_result() -> ReservedCriterionResult:
    return ReservedCriterionResult(
        planned_flow=[
            "Extract factual claims from article text.",
            "Retrieve supporting or contradicting evidence.",
            "Classify claim-evidence pairs with Ashg2099/xlm-roberta-factchecker.",
        ]
    )
