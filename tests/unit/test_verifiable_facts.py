import httpx
import pytest

from news_analysis.criteria.fact_check import FactCheckClient, evaluate_fact_checks, is_applicable_fact_check

CLAIM = "Vacina reduz casos graves"


def review(publisher, rating, url):
    return {"publisher": {"site": publisher}, "textualRating": rating, "url": url, "languageCode": "pt"}


def test_equal_weight_per_publisher_and_duplicate_exclusion():
    a = review("a.example", "Verdadeiro", "https://a.example/1")
    raw = {"claims": [{"text": CLAIM, "claimReview": [a, a, review("a.example", "Verdadeiro", "https://a.example/2"), review("b.example", "Falso", "https://b.example/1")]}]}
    result = evaluate_fact_checks(raw, CLAIM, "", "query")
    assert result.score == 0.5
    assert result.scored_reviews_count == 3
    assert result.publishers_count == 2
    assert result.publisher_scores == {"a.example": 1.0, "b.example": 0.0}
    assert result.reviews[1].exclusion_reason == "duplicate_review"
    assert result.conflicting_verdicts
    assert result.reviews[0].language == "pt"


@pytest.mark.parametrize("target,checked", [
    ("Vacina não reduz casos graves", CLAIM),
    ("É falso que vacina reduz casos graves", CLAIM),
    ("Vacina reduz casos graves em 2026", "Vacina reduz casos graves em 2020"),
    ("Vacina aumenta casos graves", CLAIM),
])
def test_opposite_or_different_claims_excluded(target, checked):
    assert not is_applicable_fact_check(target, checked, target)


def test_review_headline_cannot_override_checked_claim():
    assert not is_applicable_fact_check(CLAIM, "Preço do combustível aumenta", CLAIM)


def test_user_claim_is_scored_instead_of_debunking_article_title():
    raw = {"claims": [{"text": CLAIM, "claimant": "Pessoa", "claimDate": "2026-01-01T00:00:00Z", "claimReview": [review("a.example", "Falso", "https://a.example/1")]}]}
    result = evaluate_fact_checks(raw, "É falso que vacina reduz casos graves", "", "query", target_claim=CLAIM, claim_origin="user")
    assert result.score == 0
    assert result.target_claim == CLAIM
    assert result.claim_origin == "user"
    assert result.reviews[0].claimant == "Pessoa"


def test_identifiable_publisher_required():
    result = evaluate_fact_checks({"claims": [{"text": CLAIM, "claimReview": [{"textualRating": "Verdadeiro"}]}]}, CLAIM, "", "query")
    assert not result.available
    assert result.reviews[0].exclusion_reason == "missing_publisher_identity"


def test_pagination_keeps_query_and_language(temp_settings):
    calls = []
    def handler(request):
        calls.append(dict(request.url.params))
        if len(calls) == 1:
            return httpx.Response(200, json={"claims": [{"text": "first"}], "nextPageToken": "next"})
        return httpx.Response(200, json={"claims": [{"text": "second"}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = FactCheckClient(temp_settings, client).search(CLAIM)
    assert len(result["claims"]) == 2
    assert not result["search_truncated"]
    assert calls[1]["pageToken"] == "next"
    assert calls[0]["query"] == calls[1]["query"] == CLAIM
    assert calls[0]["languageCode"] == calls[1]["languageCode"] == "pt"


def test_pagination_bound_is_exposed(temp_settings):
    count = 0
    def handler(request):
        nonlocal count
        count += 1
        return httpx.Response(200, json={"claims": [], "nextPageToken": str(count)})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = FactCheckClient(temp_settings, client).search(CLAIM)
    assert count == 3
    assert result["search_truncated"]
