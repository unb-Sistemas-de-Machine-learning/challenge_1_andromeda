from news_analysis.criteria.fact_check import evaluate_fact_checks


def test_multiple_applicable_ratings_use_arithmetic_mean(sample_fact_check_response, long_article_text):
    sample_fact_check_response["claims"].append(
        {
            "text": "Vacina reduz casos graves",
            "languageCode": "pt",
            "claimReview": [{"title": "Vacina reduz casos graves", "textualRating": "Meia verdade"}],
        }
    )
    result = evaluate_fact_checks(sample_fact_check_response, "Vacina reduz casos graves", long_article_text, "query")
    assert result.available is True
    assert result.score == 0.75
    assert result.applicable_reviews_count == 2
