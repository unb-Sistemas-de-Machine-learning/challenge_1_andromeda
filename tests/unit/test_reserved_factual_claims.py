from news_analysis.criteria.factual_claims import reserved_factual_claims_result


def test_reserved_factual_claims_payload():
    result = reserved_factual_claims_result()
    assert result.available is False
    assert result.score is None
    assert result.status == "NOT_IMPLEMENTED"
    assert result.planned_model == "Ashg2099/xlm-roberta-factchecker"
    assert result.planned_flow
