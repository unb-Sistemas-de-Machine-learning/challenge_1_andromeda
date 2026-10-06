"""Bounded searches for a primary claim and optional, non-scoring evidence."""
from __future__ import annotations

import re
from typing import Any

from news_analysis.criteria.fact_check import (
    _clean_title, build_fact_check_queries, evaluate_fact_checks, safe_search_error,
)
from news_analysis.criteria.rating_normalization import normalize_text
from news_analysis.pipeline.models import ErrorInfo, FactCheckCriterionResult, FactCheckEvidence

MAX_CANDIDATES = 3


def select_claim_candidates(title: str | None, text: str, claim: str | None = None) -> list[tuple[str, str]]:
    """Select verbatim candidates; do not invent subjects or split conjunctions."""
    if claim and claim.strip():
        return [(claim.strip(), 'user')]
    candidates = [(_clean_title(title or ''), 'article_title')]
    candidates.extend((sentence, 'article_sentence') for sentence in
                      re.split(r'(?<=[.!?])\s+|\n+', text, maxsplit=20)[:20])
    selected: list[tuple[str, str]] = []
    seen: set[str] = set()
    for sentence, origin in candidates:
        sentence = ' '.join(sentence.split()).strip()
        normalized = normalize_text(sentence)
        if not 15 <= len(sentence) <= 500 or len(normalized.split()) < 3 or sentence.endswith('?'):
            continue
        # A repeated headline in the lead is not a second claim.
        if normalized in seen:
            continue
        seen.add(normalized)
        selected.append((sentence, origin))
        if len(selected) == MAX_CANDIDATES:
            break
    return selected


def run_fact_check_search(client: Any, title: str | None, text: str,
                          claim: str | None = None) -> FactCheckCriterionResult:
    candidates = select_claim_candidates(title, text, claim)
    if not candidates:
        result = evaluate_fact_checks({'claims': []}, None, '', '', claim_origin='no_candidate')
        result.error = ErrorInfo(code='CRITERION_UNAVAILABLE', message='No suitable claim candidate was selected.',
                                 retryable=False, details={'reason': 'no_claim_candidate'})
        return result

    results: list[FactCheckCriterionResult] = []
    # Identical queries across candidates reuse retrieval, but matching remains per claim.
    cache: dict[str, dict[str, Any]] = {}
    for target, origin in candidates:
        combined: dict[str, Any] = {'claims': [], 'search_attempts': [], 'search_incomplete': False,
                                    'search_truncated': False}
        errors: list[dict[str, Any]] = []
        stop = False
        queries = build_fact_check_queries(target, '')
        for query in queries:
            attempt: dict[str, Any] = {'query': query, 'target_claim': target}
            try:
                cached = query in cache
                raw = cache[query] if cached else client.search(query)
                # Validate this batch before merging so malformed data cannot
                # erase valid evidence from an earlier query or crash the pipeline.
                evaluate_fact_checks(raw, title, '', query, target_claim=target, claim_origin=origin)
                cache[query] = raw
                attempt.update(claims_count=len(raw.get('claims', [])), status='success', cached=cached)
                combined['claims'].extend(raw.get('claims', []))
                combined['search_truncated'] |= bool(raw.get('search_truncated'))
                if raw.get('search_incomplete'):
                    attempt['status'] = 'partial'
                    attempt['errors'] = raw.get('search_errors', [])
                    errors.extend(attempt['errors'])
                    combined['search_incomplete'] = True
                    stop = any(error.get('http_status') in {401, 403, 429} for error in attempt['errors'])
                if raw.get('unavailable_reason') == 'missing_api_key':
                    combined['unavailable_reason'] = 'missing_api_key'
                    attempt['status'] = 'skipped_missing_api_key'
                    stop = True
            except Exception as exc:
                detail = safe_search_error(exc)
                errors.append(detail)
                attempt.update(status='error', error=detail)
                combined['search_incomplete'] = True
                stop = detail.get('http_status') in {401, 403, 429}
            combined['search_attempts'].append(attempt)
            if stop:
                break
        result = evaluate_fact_checks(combined, title, '', queries[0] if queries else '',
                                      target_claim=target, claim_origin=origin)
        if errors:
            result.error = ErrorInfo(code='FACT_CHECK_API_ERROR', message='Some Fact Check searches failed; retrieved evidence was preserved.',
                                     retryable=not any(error.get('http_status') in {401, 403} for error in errors),
                                     details={'reason': 'partial_search_failure', 'errors': errors})
            if not result.available:
                result.status = 'ERROR'
        results.append(result)
        if stop:
            break
    primary = results[0]
    primary.additional_claims = [FactCheckEvidence.model_validate(
        result.model_dump(include=set(FactCheckEvidence.model_fields))) for result in results[1:]]
    return primary
