import pytest

from news_analysis.pipeline.aggregation import INTENDED_WEIGHTS, aggregate_final_score


def test_all_three_criteria_contribute_with_requested_weights():
    final = aggregate_final_score(1.0, 0.5, 50)
    assert final.score == 82.5
    assert final.coverage == 100
    assert final.intended_weights == {"verifiable_facts": 0.65, "credibility": 0.20, "writing_style": 0.15}
    assert final.effective_weights == INTENDED_WEIGHTS
    assert "0.20 * C" in final.formula


@pytest.mark.parametrize("fact,writing,source,coverage,score,weights", [
    (0.25, None, None, 65, 25, {"verifiable_facts": 1.0}),
    (None, None, 40, 20, 40, {"credibility": 1.0}),
    (None, 0.8, None, 15, 80, {"writing_style": 1.0}),
    (0.2, 0.8, None, 80, 31.25, {"verifiable_facts": 0.8125, "writing_style": 0.1875}),
    (None, 0.8, 80, 35, 80, {"credibility": 0.20 / 0.35, "writing_style": 0.15 / 0.35}),
    (0.25, None, 50, 85, 30.8824, {"verifiable_facts": 0.65 / 0.85, "credibility": 0.20 / 0.85}),
])
def test_unavailable_criteria_are_excluded_and_remaining_weights_normalized(fact, writing, source,
                                                                             coverage, score, weights):
    final = aggregate_final_score(fact, writing, source)
    assert final.coverage == coverage
    assert final.score == pytest.approx(score, abs=0.0001)
    assert final.effective_weights == pytest.approx(weights)
    assert sum(final.effective_weights.values()) == pytest.approx(1)
    assert f"/ {coverage / 100:.2f} * 100" in final.formula


def test_no_criteria_available():
    final = aggregate_final_score(None, None, None)
    assert final.score is None
    assert final.coverage == 0
    assert final.effective_weights == {}


@pytest.mark.parametrize("fact,writing,source", [(0, 0, 0), (1, 1, 100)])
def test_final_score_stays_within_zero_and_one_hundred(fact, writing, source):
    final = aggregate_final_score(fact, writing, source)
    assert 0 <= final.score <= 100
