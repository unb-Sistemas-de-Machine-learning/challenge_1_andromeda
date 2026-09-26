# Quickstart: News Analysis System Validation

This guide describes how to validate the feature after implementation. It is a
run and verification guide, not implementation code.

## Prerequisites

- Python 3.11 available locally.
- Google Fact Check Tools API key available as `FACTCHECK_API_KEY`.
- Network access for article fetching, Google Fact Check Tools API, and initial
  model download/cache.
- Dependencies installed from the implementation package once tasks create it.

## Setup

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -e .[dev]
```

Set the required API key:

```powershell
$env:FACTCHECK_API_KEY = "<your-api-key>"
```

Start the service:

```powershell
uvicorn news_analysis.api.app:app --reload
```

Open the generated API docs:

```text
http://127.0.0.1:8000/docs
```

## Contract Validation

Validate the OpenAPI contract in:

```text
specs/001-news-analysis/contracts/openapi.yaml
```

Expected endpoints:

- `POST /analyses`
- `GET /analyses/{analysis_id}`

## Scenario 1: Successful Analysis With Both Criteria

Submit a valid HTTP/HTTPS news URL that yields at least 1,000 extracted
characters and mock or configure Fact Check results with at least one applicable
normalizable rating.

Expected outcome:

- `status = SUCCESS`
- `article.extracted_character_count >= 1000`
- `criteria.source_credibility.available = true`
- `criteria.writing_style.available = true`
- `final.coverage = 100`
- `final.score` is between 0 and 100
- `final.limitation` states the score is not a probability of truth/falsity
- no full extracted article text is present in the response or stored audit
  record

## Scenario 2: Invalid URL

Submit:

```json
{
  "url": "not-a-url"
}
```

Expected outcome:

- `status = INVALID_URL`
- no final index is produced
- response includes a clear error message

## Scenario 3: Blocked Internal URL

Submit a URL resolving to localhost, loopback, private network, link-local, or
cloud metadata address.

Expected outcome:

- `status = BLOCKED_INTERNAL_URL`
- no fetch is attempted against the blocked destination
- feedback clearly says the URL was blocked for security

## Scenario 4: Fetch Limits

Use fixtures or mocks for each condition:

- fetch exceeds 10 seconds
- content exceeds 5 MB
- redirect chain exceeds 5 redirects

Expected outcome:

- fetch stops at the configured limit
- no analysis is produced from incomplete or unsafe content
- response includes an identifiable failure state

## Scenario 5: Extraction Threshold

Submit or mock a reachable page where fewer than 1,000 characters of main
article text are extracted.

Expected outcome:

- `status = ARTICLE_EXTRACTION_FAILED`
- no criterion scores are produced
- no final index is produced

## Scenario 6: Fact-Check Applicability

Mock Fact Check Tools results containing:

- one review that clearly matches the article title or main claim
- one review that does not clearly match
- one review with unmapped textual rating

Expected outcome:

- all returned reviews are preserved for traceability
- only clearly matching reviews may contribute to scoring
- unmapped ratings remain unnormalized
- multiple applicable normalized values are averaged arithmetically
- absence of applicable normalizable reviews makes the criterion unavailable
  rather than zero

## Scenario 7: Writing Classifier Long Text

Use an article long enough to exceed the classifier input limit.

Expected outcome:

- text is split into segments
- each segment has label, confidence, character count, and `writing_score`
- aggregate writing score is text-length-weighted mean of segment scores
- `segments_analyzed` equals the number of classified segments

## Scenario 8: Writing Classifier `Fake` Label

Mock or use a fixture where the writing classifier aggregate label is `Fake`.

Expected outcome:

- `criteria.writing_style.qualitative_state = "Sinal de escrita suspeito"`
- response explains that the label is a writing-style signal, not a factual
  verdict
- final score remains an operational criterion score, not a truth probability

## Scenario 9: Partial Criterion Availability

Mock one current criterion as unavailable and the other as available.

Expected outcome:

- if only fact-checking is available, `coverage = 60` and `score = C * 100`
- if only writing style is available, `coverage = 40` and `score = W * 100`
- unavailable criterion is not substituted with zero
- output explains which criterion ran and which did not

## Scenario 10: No Current Criteria Available

Mock both current criteria as unavailable.

Expected outcome:

- `final.score = null`
- `final.coverage = 0`
- both unavailable reasons are visible
- no false/true verdict is shown

## Scenario 11: Rate Limit

Submit more than 10 analysis requests for the same user within one minute.

Expected outcome:

- first 10 requests are accepted subject to normal validation
- additional requests in that minute are rejected
- response clearly states that the rate limit was reached

## Automated Test Targets

```powershell
pytest tests/unit
pytest tests/contract
pytest tests/integration
```

Minimum expected coverage before implementation is considered complete:

- URL validation and blocking
- article fetch limits
- article extraction threshold
- Fact Check Tools response preservation, applicability, normalization, and
  aggregation
- writing classifier label mapping, segmentation, and weighted aggregation
- final score and coverage formulas
- audit record persistence without full extracted article text
- rate limiting

## Validation Notes

Automated validation was run with mocked article fetching, mocked Fact Check
Tools responses, deterministic writing-style classification, temporary SQLite
storage, and FastAPI TestClient. The test suite covers the scenarios above
without requiring live network calls, real Google API credentials, or model
downloads during tests.

Latest validation command:

```powershell
uv run --extra dev --python "C:\Users\dvmrn\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" pytest tests/unit tests/contract tests/integration
```

Latest result:

```text
41 passed, 1 warning
```
