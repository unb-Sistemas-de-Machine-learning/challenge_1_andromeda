# Quickstart: News Analysis System Validation

This guide describes how to validate the feature after implementation. It is a
run and verification guide, not implementation code.

## Prerequisites

- Python 3.11 or newer and uv available locally.
- Google Fact Check Tools API key as `FACTCHECK_API_KEY` for the fact-check criterion; writing inference does not require it.
- Network access for article fetching, Google Fact Check Tools API, and initial
  model download/cache.
- Dependencies installed from `pyproject.toml`.

## Setup

```powershell
uv sync --extra dev
uv run python teste_bertimbau.py --texto "A reportagem desmente um boato sobre a saúde."
```

The script runs the application's actual CPU classifier, downloads pinned
weights if absent, and reports class, confidence, score, segment count, and
revision. Subsequent executions reuse the disk cache; the server loads its own
in-memory instance. Optionally set `NEWS_ANALYSIS_MODEL_CACHE` to select the
Hugging Face cache directory.

Set the fact-check API key:

```powershell
$env:FACTCHECK_API_KEY = "<your-api-key>"
```

Start the service:

```powershell
uv run uvicorn news_analysis.api.app:app --reload
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
- `criteria.verifiable_facts.available = true`
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

- one review that clearly matches the selected claim
- one review that does not clearly match
- one review with unmapped textual rating

Expected outcome:

- all returned reviews are preserved for traceability
- only clearly matching reviews may contribute to scoring
- unmapped ratings remain unnormalized
- matching uses `Claim.text`, not review headlines, and rejects numeric/negation differences
- duplicate reviews and unidentified publishers do not contribute
- mapped whole labels are averaged per publisher, then equally across publishers
- original verdicts, inclusion/exclusion reasons and divergence remain visible
- absence of applicable normalizable reviews makes the criterion unavailable
  rather than zero

## Scenario 7: Writing Classifier Long Text

Use an article long enough to exceed the classifier input limit.

Expected outcome:

- all tokenized extracted text is processed in non-overlapping overflow windows
- each input has at most 512 tokens including special tokens; no overflow is discarded
- each segment has label, confidence, character count, actual token count, and `writing_score = P_model(True)`
- aggregate writing score is the character-count-weighted mean of segment scores
- `segments_analyzed` equals the number of classified segments
- aggregate class is `True` for a mean of at least 0.5, otherwise `Fake`; aggregate confidence is the mean or its complement
- the interface displays model, revision, segment count, aggregate class, and confidence
- segments are token windows, not sentences or paragraphs

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

- if only fact-checking is available, `coverage = 60` and `score = F * 100`
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
uv run pytest tests/unit tests/contract tests/integration
```

Minimum expected coverage before implementation is considered complete:

- URL validation and blocking
- article fetch limits
- article extraction threshold
- Fact Check Tools response preservation, applicability, normalization, and
  aggregation
- writing classifier label mapping, segmentation, and weighted aggregation
- final score and coverage formulas
- UI rendering for unavailable, absent and legacy fact-check payloads,
  evidence escaping, recorded queries and expandable writing-segment details
- audit record persistence without full extracted article text
- rate limiting

## Validation Notes

Automated validation was run with mocked article fetching, mocked Fact Check
Tools responses, deterministic tokenizer/model doubles, temporary SQLite
storage, and FastAPI TestClient. The test suite covers the scenarios above
without requiring live network calls, real Google API credentials, or model
downloads during tests.

Latest validation command:

```powershell
uv run pytest
```

Latest result:

```text
75 passed, 1 warning
```

Real-weight validation exercises `POST /analyses` and
`GET /analyses/{analysis_id}` with controlled article/fact-check inputs, CPU
BERTimbau inference, multiple token windows, writing-only coverage of 15%, and
SQLite audit retrieval. A second classification confirms in-process model reuse.

## Scenario 12: Writing Model Failure

Simulate a weight-loading or inference failure. Expect writing availability
`false`, criterion status `ERROR`, error code `WRITING_MODEL_ERROR`, no score,
no prediction, and zero reported completed segments. No keyword fallback runs.
With fact-checking and source credibility available, the analysis remains
`SUCCESS` with coverage 85%; their effective weights are renormalized to
65/85 and 20/85. If the source is also unavailable, fact-checking alone has
coverage 65% and effective weight 100%.

## Scenario 13: Selected Verifiable Claim

Submit a URL with optional `claim` of 3 to 500 characters. Response fields
`criteria.verifiable_facts.target_claim` and `claim_origin=user` identify scope.
The note concerns that assertion, not the article's endorsement or source reputation.
Writing classification still uses the article text. Verify original verdicts,
evidence URLs, scoring exclusions, publisher means, divergence and search limits.

## Scenario 14: Unavailable Facts in the Interface

Render a response with `criteria.verifiable_facts.available=false` and a
writing-only score of 100 with source credibility unavailable. Expect the fact-check card to remain visible, show
status, reason, counts and recorded queries, and the summary to say
that only writing contributed, with coverage 15%. It must not present the score
as confirmation of the article's facts. An absent criterion must produce an
explicit missing-data notice; a legacy `source_credibility` response must remain
readable without inventing new scoring metadata.

## Scenario 15: Writing Segment Details

Expand "Resultados por segmento". Verify each input window displays index,
characters, actual model tokens including special tokens, class, confidence and
writing score, consistently with `criteria.writing_style.segments` in JSON.
Summary formula and analysis ID must be visible. Node-executed rendering tests
in `tests/unit/test_frontend_rendering.py` check these behaviors when Node.js is
available; environments without Node.js skip those rendering tests.
