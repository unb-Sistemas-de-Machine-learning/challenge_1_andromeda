from news_analysis.criteria.fact_check import evaluate_fact_checks, is_applicable_fact_check


def test_applicability_requires_normalized_claim_overlap():
    assert is_applicable_fact_check("Vacina reduz casos graves", "Vacina reduz casos graves em idosos", None)
    assert not is_applicable_fact_check("Vacina reduz casos graves", "Preço do combustível aumenta", None)


def test_preserves_but_excludes_non_applicable_reviews(long_article_text):
    raw = {
        "claims": [
            {"text": "Preço do combustível aumenta", "claimReview": [{"title": "Combustível aumenta", "textualRating": "Falso"}]}
        ]
    }
    result = evaluate_fact_checks(raw, "Vacina reduz casos graves", long_article_text, "query")
    assert result.available is False
    assert result.reviews_count == 1
    assert result.reviews[0].applicable is False
    assert result.reviews[0].normalized_value == 0.0
