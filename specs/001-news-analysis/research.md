# Phase 0 Research: News Analysis System

## Decision: Python 3.11 Backend Service

**Rationale**: The feature depends on article fetching, HTML extraction,
structured JSON contracts, Hugging Face Transformers/PyTorch inference, and
Google Fact Check Tools API integration. Python has mature libraries for each
concern and fits the project documentation around machine learning exploration.

**Alternatives considered**:

- Node.js service: good HTTP tooling, weaker fit for the specified model
  inference stack.
- Notebook-only workflow: useful for exploration, but does not satisfy URL-based
  analysis, contracts, audit records, and rate limiting.

## Decision: FastAPI With Pydantic Schemas

**Rationale**: The feature needs a small HTTP/JSON interface, explicit request
and response validation, and generated OpenAPI documentation. FastAPI and
Pydantic provide this with low ceremony while keeping contract tests direct.

**Alternatives considered**:

- Flask: simpler but requires more manual validation and OpenAPI work.
- CLI-only interface: easier to build, but less aligned with the structured
  result contract and future integration needs.

## Decision: SQLite Audit Storage for MVP

**Rationale**: The MVP needs durable audit records, not high-scale multi-user
operations. SQLite keeps setup simple and supports structured persistence for
analysis metadata, raw external responses, model outputs, normalized scores,
weights, coverage, and pipeline versions. Full extracted text remains transient
and is not stored.

**Alternatives considered**:

- JSONL files: simple but weaker for querying records by analysis id, status, or
  criterion.
- PostgreSQL: appropriate later, but adds operational overhead before there is
  scale pressure.
- No persistence: violates traceability and audit requirements.

## Decision: trafilatura for Article Extraction With Safety Wrapper

**Rationale**: The system must extract main article text and metadata from
arbitrary news pages while preserving semantic content. `trafilatura` is
designed for article extraction and can be wrapped with explicit fetch limits,
URL blocking, and metadata validation.

**Alternatives considered**:

- BeautifulSoup-only extraction: flexible but would require substantial custom
  heuristics.
- Browser automation: heavier, higher security risk, and conflicts with the
  requirement to avoid arbitrary JavaScript execution from analyzed pages.

## Decision: httpx for Outbound HTTP With Strict Safety Controls

**Rationale**: `httpx` supports explicit timeouts, redirect control, streaming
downloads, and test mocking. The fetcher can enforce HTTP/HTTPS only, DNS/IP
blocking for internal destinations, 10-second timeout, 5 MB content cap, 5
redirect cap, and clear error states.

**Alternatives considered**:

- requests: familiar but less ergonomic for streaming limits and async migration.
- Browser fetch: unnecessary and riskier for untrusted content.

## Decision: Google Fact Check Tools `claims.search` Only

**Rationale**: The current feature uses published fact-check reviews as a
criterion. The local manual documents `claims.search` as the read-only endpoint
for text queries. `pages.*` endpoints are for publishers managing ClaimReview
markup and are outside the consumer analysis scope.

**Alternatives considered**:

- `claims.imageSearch`: out of scope because current input is one news URL.
- `pages.*`: requires OAuth and manages publisher markup rather than searching
  for related checks.

## Decision: Combined Title Plus Representative Excerpt Query

**Rationale**: The clarified spec requires one combined query using the article
title and representative main-text excerpt when both are available. This gives
the lookup more context than title alone while remaining deterministic.

**Alternatives considered**:

- Title-only query: simpler but may miss checks when titles are rewritten.
- Excerpt-only query: may lose the editorial claim framing from the title.
- Multiple fallback queries: higher recall, but more complex than current scope.

## Decision: Applicable Fact Checks Require Clear Match

**Rationale**: The Fact Check Tools API can return related but non-identical
claims. A returned review contributes to the score only when its checked claim or
review title clearly matches the article title or main claim. Non-matching
results are preserved for traceability but excluded from scoring.

**Alternatives considered**:

- Use all API results: too noisy and risks false attribution.
- Same-domain only: too restrictive because fact-check organizations review
  claims from many domains.
- Portuguese-only: useful as a filter, but language alone does not establish
  applicability.

## Decision: Direct Transformers/PyTorch Model Inference

**Rationale**: The writing criterion requires preserving predicted class,
confidence, segment counts, segment-level scores, and model version. Direct
model/tokenizer loading gives more control over segmentation and traceability
than a high-level wrapper.

**Alternatives considered**:

- Transformers pipeline: faster to prototype but less explicit for segmentation,
  labels, and version capture.
- External model service: possible later, but adds deployment complexity.

## Decision: Segment Long Text and Use Text-Length-Weighted Mean

**Rationale**: The model limit is around 512 tokens. The spec clarifies that long
articles must be segmented and segment `writing_score` values aggregated by text
length. This prevents silent truncation and reduces distortion from uneven
segment sizes.

**Alternatives considered**:

- Truncate to first segment: violates coverage and may discard important text.
- Arithmetic mean: simpler but overweights short segments.
- Minimum score: overly conservative and less representative.

## Decision: Operational Score With Explicit Coverage

**Rationale**: The constitution and spec forbid treating the final index as a
truth probability. The final score is an operational weighted combination of
available criteria, and coverage communicates how much of the intended current
analysis ran.

**Alternatives considered**:

- Probability-like output: rejected because it overstates what the criteria
  prove.
- Boolean true/false result: rejected because it conflicts with system
  limitations.

## Decision: Preserve Raw Evidence, Not Full Article Text

**Rationale**: Traceability requires enough data to reconstruct criterion
decisions, while the clarified spec rejects retaining full extracted article text
after analysis. The audit record keeps URL data, metadata, content hash, raw
external responses, model outputs, normalized scores, weights, coverage, final
score, and versions.

**Alternatives considered**:

- Store full text indefinitely: strongest reproducibility but unnecessary
  retention risk.
- Store no raw evidence: weakens auditability and violates traceability.

## Decision: Local Rate Limiting per User

**Rationale**: The clarified spec sets an initial limit of 10 analyses per minute
per user. The MVP can enforce this at the application layer with a simple
in-memory or SQLite-backed counter, while exposing clear feedback when the limit
is reached.

**Alternatives considered**:

- No rate limit: violates antiabuse requirements.
- External gateway only: useful later, but should not be the only source of
  product behavior in the MVP.
