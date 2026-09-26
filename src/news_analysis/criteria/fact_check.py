from __future__ import annotations

from typing import Any

import httpx

from news_analysis.config import Settings
from news_analysis.criteria.rating_normalization import normalize_rating, normalize_text
from news_analysis.pipeline.errors import CriterionStatus
from news_analysis.pipeline.models import ErrorInfo, FactCheckCriterionResult, FactCheckReview

STOPWORDS = {
    "a", "o", "os", "as", "um", "uma", "de", "da", "do", "das", "dos", "em",
    "no", "na", "nos", "nas", "para", "por", "com", "que", "e", "ou", "the",
    "of", "to", "in", "on", "for", "and", "or", "is", "are",
}


class FactCheckClient:
    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self.settings = settings
        self.client = client

    def search(self, query: str) -> dict[str, Any]:
        if not self.settings.factcheck_api_key:
            return {"claims": []}
        close_client = self.client is None
        client = self.client or httpx.Client(timeout=10)
        try:
            response = client.get(
                "https://factchecktools.googleapis.com/v1alpha1/claims:search",
                params={"query": query, "key": self.settings.factcheck_api_key},
            )
            response.raise_for_status()
            return response.json()
        finally:
            if close_client:
                client.close()


def build_fact_check_query(title: str | None, main_text: str) -> str:
    excerpt = " ".join(main_text.split())[:500]
    if title and excerpt:
        return f"{title} {excerpt}"
    return title or excerpt


def evaluate_fact_checks(raw: dict[str, Any], article_title: str | None, main_text: str, query: str) -> FactCheckCriterionResult:
    reviews = _flatten_reviews(raw)
    processed: list[FactCheckReview] = []
    normalizable: list[float] = []
    main_claim = article_title or main_text[:240]

    for review in reviews:
        textual_rating = review.get("textual_rating")
        normalized_value = normalize_rating(textual_rating)
        applicable = is_applicable_fact_check(
            main_claim=main_claim,
            checked_claim=review.get("claim"),
            review_title=review.get("review_title"),
        )
        if applicable and normalized_value is not None:
            normalizable.append(normalized_value)
        processed.append(
            FactCheckReview(
                claim=review.get("claim"),
                publisher_name=review.get("publisher_name"),
                publisher_site=review.get("publisher_site"),
                review_url=review.get("review_url"),
                review_title=review.get("review_title"),
                review_date=review.get("review_date"),
                textual_rating=textual_rating,
                language=review.get("language"),
                applicable=applicable,
                normalized_value=normalized_value,
                raw=review.get("raw", review),
            )
        )

    if not normalizable:
        return FactCheckCriterionResult(
            available=False,
            status=CriterionStatus.UNAVAILABLE,
            score=None,
            query=query,
            reviews_count=len(processed),
            applicable_reviews_count=sum(1 for review in processed if review.applicable),
            reviews=processed,
            error=ErrorInfo(
                code="CRITERION_UNAVAILABLE",
                message="No applicable normalizable fact-check review was available.",
                retryable=False,
            ),
        )

    return FactCheckCriterionResult(
        available=True,
        status=CriterionStatus.EXECUTED,
        score=round(sum(normalizable) / len(normalizable), 4),
        query=query,
        reviews_count=len(processed),
        applicable_reviews_count=sum(1 for review in processed if review.applicable),
        reviews=processed,
    )


def unavailable_fact_check(query: str, message: str = "Fact-check criterion unavailable.") -> FactCheckCriterionResult:
    return FactCheckCriterionResult(
        available=False,
        status=CriterionStatus.UNAVAILABLE,
        score=None,
        query=query,
        reviews_count=0,
        applicable_reviews_count=0,
        reviews=[],
        error=ErrorInfo(code="CRITERION_UNAVAILABLE", message=message, retryable=False),
    )


def error_fact_check(query: str, exc: Exception) -> FactCheckCriterionResult:
    return FactCheckCriterionResult(
        available=False,
        status=CriterionStatus.ERROR,
        score=None,
        query=query,
        reviews_count=0,
        applicable_reviews_count=0,
        reviews=[],
        error=ErrorInfo(code="FACT_CHECK_API_ERROR", message="Fact Check Tools API failed.", retryable=True, details={"reason": exc.__class__.__name__}),
    )


def is_applicable_fact_check(main_claim: str | None, checked_claim: str | None, review_title: str | None) -> bool:
    source_tokens = _meaningful_tokens(main_claim or "")
    if not source_tokens:
        return False
    candidates = [_meaningful_tokens(checked_claim or ""), _meaningful_tokens(review_title or "")]
    for candidate in candidates:
        if not candidate:
            continue
        overlap = source_tokens & candidate
        denominator = max(3, min(len(source_tokens), len(candidate)))
        if len(overlap) / denominator >= 0.5:
            return True
    return False


def _meaningful_tokens(value: str) -> set[str]:
    tokens = normalize_text(value).split()
    return {token for token in tokens if len(token) > 2 and token not in STOPWORDS}


def _flatten_reviews(raw: dict[str, Any]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for claim in raw.get("claims", []):
        claim_text = claim.get("text")
        language = claim.get("languageCode")
        for review in claim.get("claimReview", []) or []:
            publisher = review.get("publisher") or {}
            flattened.append(
                {
                    "claim": claim_text,
                    "publisher_name": publisher.get("name"),
                    "publisher_site": publisher.get("site"),
                    "review_url": review.get("url"),
                    "review_title": review.get("title"),
                    "review_date": review.get("reviewDate"),
                    "textual_rating": review.get("textualRating"),
                    "language": language,
                    "raw": {"claim": claim, "claimReview": review},
                }
            )
    return flattened
