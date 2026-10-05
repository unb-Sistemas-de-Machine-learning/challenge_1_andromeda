from news_analysis.pipeline.aggregation import aggregate_final_score


def test_final_score_all_criteria():
    final = aggregate_final_score(1.0, 0.5, 0.75)
    assert final.score == 80
    assert final.coverage == 100
    assert final.effective_weights == {"verifiable_facts": 0.5, "writing_style": 0.3, "source_credibility": 0.2}


def test_final_score_fact_check_only():
    final = aggregate_final_score(0.25, None, None)
    assert final.score == 25
    assert final.coverage == 50
    assert final.effective_weights == {"verifiable_facts": 1.0}


def test_final_score_writing_only():
    final = aggregate_final_score(None, 0.8, None)
    assert final.score == 80
    assert final.coverage == 30
    assert final.effective_weights == {"writing_style": 1.0}


def test_final_score_credibility_only():
    final = aggregate_final_score(None, None, 0.35)
    assert final.score == 35
    assert final.coverage == 20
    assert final.effective_weights == {"source_credibility": 1.0}


def test_final_score_no_criteria_available():
    final = aggregate_final_score(None, None, None)
    assert final.score is None
    assert final.coverage == 0
    assert final.effective_weights == {}
