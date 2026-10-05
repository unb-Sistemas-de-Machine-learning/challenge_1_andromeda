from __future__ import annotations

from typing import Any
from collections import defaultdict
from urllib.parse import urlsplit
import re

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
            return {"claims": [], "unavailable_reason": "missing_api_key"}
        close_client = self.client is None
        client = self.client or httpx.Client(timeout=10)
        try:
            params = {"query": query, "key": self.settings.factcheck_api_key, "pageSize": 10, "languageCode": "pt"}
            claims = []
            seen_tokens = set()
            for _ in range(3):
                response = client.get(
                    "https://factchecktools.googleapis.com/v1alpha1/claims:search", params=params,
                )
                response.raise_for_status()
                page = response.json()
                claims.extend(page.get("claims", []))
                token = page.get("nextPageToken")
                if not token:
                    return {"claims": claims, "search_truncated": False}
                if token in seen_tokens:
                    break
                seen_tokens.add(token)
                params = {**params, "pageToken": token}
            return {"claims": claims, "search_truncated": True}
        finally:
            if close_client:
                client.close()


def build_fact_check_query(title: str | None, main_text: str) -> str:
    excerpt = " ".join(main_text.split())[:240]
    if title and excerpt:
        return f"{title} {excerpt}"
    return title or excerpt


def build_fact_check_queries(title: str | None, main_text: str) -> list[str]:
    text = " ".join(main_text.split())
    clean_title = _clean_title(title or "")
    candidates = [
        build_fact_check_query(clean_title or title, text),
        title or "",
        clean_title,
        _first_sentence(text),
        text[:180],
        _keyword_query(clean_title or title, text),
    ]
    queries: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        query = " ".join(candidate.split()).strip()
        if len(query) > 300:
            query = query[:300].rsplit(" ", 1)[0]
        if query and query not in seen:
            seen.add(query)
            queries.append(query)
    return queries


def evaluate_fact_checks(raw: dict[str, Any], article_title: str | None, main_text: str, query: str, *, target_claim: str | None = None, claim_origin: str = "article_title_or_excerpt") -> FactCheckCriterionResult:
    reviews = _flatten_reviews(raw)
    processed: list[FactCheckReview] = []
    by_publisher: dict[str, list[float]] = defaultdict(list)
    seen = set()
    main_claim = target_claim or _clean_title(article_title or "") or _first_sentence(main_text)

    for review in reviews:
        textual_rating = review.get("textual_rating")
        normalized_value = normalize_rating(textual_rating)
        applicable = is_applicable_fact_check(
            main_claim=main_claim,
            checked_claim=review.get("claim"),
            review_title=review.get("review_title"),
        )
        publisher_key = _publisher_key(review)
        identity = (review.get("review_url"), normalize_text(review.get("claim") or "")) if review.get("review_url") else (
            publisher_key, normalize_text(review.get("claim") or ""), review.get("review_date"), textual_rating,
        )
        reason = None
        if not applicable:
            reason = "claim_mismatch"
        elif normalized_value is None:
            reason = "unmapped_rating"
        elif publisher_key is None:
            reason = "missing_publisher_identity"
        elif identity in seen:
            reason = "duplicate_review"
        included = reason is None
        if included:
            seen.add(identity)
            by_publisher[publisher_key].append(normalized_value)
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
                claimant=review.get("claimant"),
                claim_date=review.get("claim_date"),
                applicable=applicable,
                included_in_score=included,
                exclusion_reason=reason,
                publisher_key=publisher_key,
                normalized_value=normalized_value,
                raw=review.get("raw", review),
            )
        )

    metadata = dict(
        target_claim=main_claim, claim_origin=claim_origin,
        search_attempts=raw.get("search_attempts", []),
        search_truncated=bool(raw.get("search_truncated")),
    )
    if not by_publisher:
        message, details = _unavailable_message(raw, processed)
        return FactCheckCriterionResult(
            available=False,
            status=CriterionStatus.UNAVAILABLE,
            score=None,
            query=query,
            reviews_count=len(processed),
            applicable_reviews_count=sum(1 for review in processed if review.applicable),
            reviews=processed,
            **metadata,
            error=ErrorInfo(
                code="CRITERION_UNAVAILABLE",
                message=message,
                retryable=False,
                details=details,
            ),
        )

    publisher_scores = {key: sum(values) / len(values) for key, values in by_publisher.items()}
    included_values = [review.normalized_value for review in processed if review.included_in_score]
    return FactCheckCriterionResult(
        available=True,
        status=CriterionStatus.EXECUTED,
        score=round(sum(publisher_scores.values()) / len(publisher_scores), 4),
        query=query,
        reviews_count=len(processed),
        applicable_reviews_count=sum(1 for review in processed if review.applicable),
        reviews=processed,
        scored_reviews_count=len(included_values),
        publishers_count=len(publisher_scores),
        publisher_scores=publisher_scores,
        conflicting_verdicts=min(included_values) < 0.5 < max(included_values),
        **metadata,
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
    # Match the reviewed claim, never the fact-check headline (which may deny it).
    source = normalize_text(main_claim or "")
    checked = normalize_text(checked_claim or "")
    if not source or not checked:
        return False
    negations = {"nao", "nunca", "jamais", "not", "never", "sem"}
    if bool(set(source.split()) & negations) != bool(set(checked.split()) & negations):
        return False
    debunking = {"falso", "fake", "boato", "mentira", "desmente", "desmentido", "enganoso"}
    if bool(set(source.split()) & debunking) != bool(set(checked.split()) & debunking):
        return False
    if re.findall(r"\d+(?:[.,]\d+)*", main_claim or "") != re.findall(r"\d+(?:[.,]\d+)*", checked_claim or ""):
        return False
    if source == checked:
        return True
    source_tokens = _meaningful_tokens(main_claim or "")
    if not source_tokens:
        return False
    candidates = [_meaningful_tokens(checked_claim or "")]
    for candidate in candidates:
        if not candidate:
            continue
        overlap = source_tokens & candidate
        if len(overlap) >= 3 and len(overlap) / len(source_tokens) >= 0.8 and len(overlap) / len(candidate) >= 0.8:
            return True
    return False


def _meaningful_tokens(value: str) -> set[str]:
    tokens = normalize_text(value).split()
    return {token for token in tokens if len(token) > 2 and token not in STOPWORDS}


def _meaningful_tokens_ordered(value: str) -> list[str]:
    tokens = normalize_text(value).split()
    ordered: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if len(token) <= 2 or token in STOPWORDS or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def _clean_title(title: str) -> str:
    for separator in [" | ", " - ", " — "]:
        if separator in title:
            return title.split(separator, 1)[0].strip()
    return title.strip()


def _first_sentence(text: str) -> str:
    for separator in [". ", "! ", "? ", "\n"]:
        if separator in text:
            return text.split(separator, 1)[0]
    return text[:180]


def _keyword_query(title: str | None, text: str) -> str:
    tokens = _meaningful_tokens_ordered(f"{title or ''} {text[:500]}")
    return " ".join(tokens[:10])


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
                    "claimant": claim.get("claimant"),
                    "claim_date": claim.get("claimDate"),
                    "publisher_name": publisher.get("name"),
                    "publisher_site": publisher.get("site"),
                    "review_url": review.get("url"),
                    "review_title": review.get("title"),
                    "review_date": review.get("reviewDate"),
                    "textual_rating": review.get("textualRating"),
                    "language": review.get("languageCode") or language,
                    "raw": {"claim": claim, "claimReview": review},
                }
            )
    return flattened


def _unavailable_message(raw: dict[str, Any], processed: list[FactCheckReview]) -> tuple[str, dict[str, Any]]:
    if raw.get("unavailable_reason") == "missing_api_key":
        return (
            "Fact-checking was skipped because FACTCHECK_API_KEY is not configured. Set it before starting the server.",
            {"reason": "missing_api_key"},
        )
    if not processed:
        attempts = raw.get("search_attempts") or []
        attempted_queries = [attempt.get("query") for attempt in attempts if attempt.get("query")]
        return (
            "Google Fact Check Tools returned no published fact-check reviews for the attempted queries.",
            {"reason": "no_reviews_returned", "attempted_queries": attempted_queries},
        )
    applicable_count = sum(1 for review in processed if review.applicable)
    if applicable_count == 0:
        return (
            "Fact-check reviews were found, but none clearly matched the article title or main claim.",
            {"reason": "no_applicable_reviews", "reviews_count": len(processed)},
        )
    if any(review.applicable and review.normalized_value is not None for review in processed):
        return ("Matched reviews lack an identifiable checking publisher.", {"reason": "missing_publisher_identity"})
    return (
        "Applicable fact-check reviews were found, but their textual ratings could not be normalized by the documented mapping.",
        {"reason": "no_normalizable_ratings", "applicable_reviews_count": applicable_count},
    )


def _publisher_key(review: dict[str, Any]) -> str | None:
    site = review.get("publisher_site") or ""
    if site:
        host = urlsplit(site if "://" in site else "https://" + site).hostname
        if host:
            return host.lower().removeprefix("www.")
    url = review.get("review_url") or ""
    host = urlsplit(url).hostname
    if host:
        return host.lower().removeprefix("www.")
    name = normalize_text(review.get("publisher_name") or "")
    return "name:" + name if name else None
