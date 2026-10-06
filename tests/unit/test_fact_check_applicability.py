from news_analysis.criteria.fact_check import build_fact_check_queries, evaluate_fact_checks, is_applicable_fact_check


def test_build_fact_check_queries_starts_with_claim_without_article_body(long_article_text):
    queries = build_fact_check_queries("Vacina reduz os casos graves", long_article_text)
    assert queries == ["Vacina reduz os casos graves", "vacina reduz casos graves"]
    assert all('Texto principal' not in query for query in queries)


def test_missing_fact_check_api_key_gets_specific_unavailable_message(long_article_text):
    result = evaluate_fact_checks(
        {"claims": [], "unavailable_reason": "missing_api_key"},
        "Vacina reduz casos graves",
        long_article_text,
        "query",
    )
    assert result.available is False
    assert "FACTCHECK_API_KEY" in result.error.message
    assert result.error.details["reason"] == "missing_api_key"


def test_no_fact_check_reviews_gets_specific_message(long_article_text):
    result = evaluate_fact_checks({"claims": []}, "Vacina reduz casos graves", long_article_text, "query")
    assert result.available is False
    assert "returned no published fact-check reviews" in result.error.message
    assert result.error.details["reason"] == "no_reviews_returned"


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
    assert result.error.details["reason"] == "no_applicable_reviews"
