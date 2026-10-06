# Implementation Plan: News Analysis System

**Branch**: `001-news-analysis` | **Date**: 2026-09-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-news-analysis/spec.md`

## Summary

Build an auditable news-analysis service that receives one HTTP/HTTPS news URL,
extracts the main article content, evaluates two current criteria, and returns a
transparent reliability index with criterion coverage and traceability metadata.
The implementation will be a Python backend service with a small HTTP/JSON
contract, local audit storage, strict URL safety controls, Google Fact Check
Tools lookup, and Hugging Face model inference for Portuguese writing style.

Writing inference uses `AutoTokenizer` with fast token offsets and
`AutoModelForSequenceClassification` on CPU in evaluation/inference mode.
Tokenizer and weights are loaded lazily and cached by cache directory per
process; a lock serializes loading and inference. Revision
`86971e56e7f5ad781cf56673df73a57375455793` is pinned. Tokenizer overflow windows
cover the complete extracted text without overlap, with at most 512 tokens
including special tokens per window. Softmax class index 1 supplies each
writing score, aggregated by character count. Model failure makes the
criterion unavailable; no rule-based substitute is executed.

`NEWS_ANALYSIS_MODEL_CACHE` selects the optional Hugging Face cache directory.
The HTML interface displays model, revision, segment count, aggregate class,
and aggregate confidence. Expandable per-segment details show character/token
counts and model predictions; JSON and audit records retain these outputs.
The fact-check card is always rendered, including absence/unavailability reasons,
status, weights, counts, original evidence and recorded queries. The renderer
accepts legacy `source_credibility` payloads with explicit compatibility feedback.
The summary identifies writing-only results and exposes formula and analysis ID.
Node-executed rendering regression tests cover current/legacy/missing payloads,
all recorded queries, escaped evidence and per-segment details.
`analysis-rules-v6-source-abstention-history` identifies the current rules.
The independent Atlas source score can cap the 60/40 averaging result at 35;
complete source unavailability abstains. Store the pre-veto mean, whether a cap
was applied, effective source policy/hash, blocklist state/hash and veto reason.
Historical metadata results using 50/30/20 remain readable in their original
`source_credibility` field, separately from facts, without rescoring or writes.
The [reconciliation decision](../../docs/DecisaoCredibilidade.md) supersedes the
discarded branch's scoring policy for new analyses.

Criterion 1 is `verifiable_facts`, named "Checagem de fatos verificáveis".
Optional `claim` selects one statement; without it the cleaned title or first
sentence is a candidate. Google retrieves reviews of claims, not source ratings.
At most three pages are fetched per query. Lexical matching uses `Claim.text`,
numeric/negation/debunking guards and 80% bidirectional token overlap or exact
equality. Whole-label mapping, deduplication and equal-weight publisher means
define the score. Original verdicts, exclusions, divergence and scope are exposed.
Historic records are projected into the new key without changing original scores
or pipeline versions.


## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI, Pydantic, httpx, trafilatura, transformers,
PyTorch, sqlite3, pytest, respx

**Storage**: SQLite audit database for analysis records, criterion outputs,
pipeline version, metadata, hashes, external responses, and model outputs. Full
extracted article text is transient only and is not retained after analysis.

**Testing**: pytest for unit/integration tests; respx or equivalent HTTP mocking
for article fetch and Google Fact Check Tools API behavior; FastAPI TestClient
for contract tests.

**Target Platform**: Local/server Python service running on a networked machine
with outbound HTTPS access to news pages, Google Fact Check Tools API, and model
download/cache during setup.

**Project Type**: Backend web service with internal analysis pipeline modules.

**Performance Goals**: Enforce 10-second article fetch timeout, maximum 5 MB
downloaded content, maximum 5 redirects, and maximum 10 analyses per minute per
user. For validation fixtures and cached model weights, successful analyses
should complete within 30 seconds on CPU for ordinary articles under the 5 MB
fetch limit.

**Constraints**: Block localhost, loopback, private network ranges, link-local
addresses, and cloud metadata addresses; accept only HTTP/HTTPS URLs; protect
API keys through environment variables; preserve raw criterion evidence without
inventing unavailable fields; do not present model predictions or final scores as
truth probabilities.

**Scale/Scope**: Academic MVP for one feature branch, optimized for correctness,
traceability, and explainability rather than high throughput. Initial scope is
single-URL synchronous analysis with local storage and explicit future migration
paths for background workers or external databases.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **C01 Transparencia**: PASS. Every score must expose source, rule, normalized
  value, weight, and contribution.
- **C02 Rastreabilidade**: PASS. Plan includes audit records with input URL,
  final URL, metadata, raw external responses, original model outputs, scores,
  weights, coverage, versions, and content hash.
- **C03 Nao Inferencia Indevida**: PASS. Contracts and UX labels must state that
  the final score and writing label are not factual verdicts.
- **C04 Ausencia de Evidencia**: PASS. Unavailable criteria are excluded from
  aggregation and never treated as zero or as negative evidence.
- **C05 Independencia**: PASS. Fact-checking and writing-style criteria are
  computed separately before aggregation.
- **C06 Explicabilidade**: PASS. Result contract includes criterion-level
  originals, normalized values, weights, contribution, and evidence.
- **C07 Integridade**: PASS. Missing metadata and unmapped ratings remain
  unavailable/original; the system must not fabricate values.
- **C08 Versionamento**: PASS. PipelineVersion is modeled and attached to every
  analysis.
- **C09 Cobertura**: PASS. Coverage is explicit and based on current criteria
  only.
- **C10 Limitacao**: PASS. The index is operational and not a probability of
  truth or falsity.

No constitution violations require justification.

## Project Structure

### Documentation (this feature)

```text
specs/001-news-analysis/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── openapi.yaml
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── news_analysis/
│   ├── api/
│   │   ├── app.py
│   │   ├── dependencies.py
│   │   └── schemas.py
│   ├── pipeline/
│   │   ├── analyzer.py
│   │   ├── aggregation.py
│   │   ├── coverage.py
│   │   └── version.py
│   ├── article/
│   │   ├── fetcher.py
│   │   ├── extractor.py
│   │   └── safety.py
│   ├── criteria/
│   │   ├── fact_check.py
│   │   ├── rating_normalization.py
│   │   └── writing_style.py
│   └── storage/
│       ├── audit_repository.py
│       └── schema.py

tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: Use a single Python backend package under
`src/news_analysis` because the feature is one cohesive analysis pipeline with a
small HTTP surface. Separate subpackages keep source fetching, criteria,
aggregation, API contracts, and storage independently testable.

## Phase 0 Research Summary

Research decisions are documented in [research.md](./research.md). All planning
unknowns were resolved without adding spec clarifications.

## Phase 1 Design Summary

- Data model: [data-model.md](./data-model.md)
- HTTP/API contract: [contracts/openapi.yaml](./contracts/openapi.yaml)
- Validation guide: [quickstart.md](./quickstart.md)

## Post-Design Constitution Check

- **Transparency**: PASS. The API contract requires original values, normalized
  values, method/model, weights, and contribution for each criterion.
- **Traceability**: PASS. Data model includes Analysis, Article, CriterionResult,
  FactCheckReview, WritingClassification, PipelineVersion, and AuditRecord
  fields.
- **No improper inference**: PASS. Contract includes `limitations` and
  non-verdict labels.
- **Unavailable data handling**: PASS. Contract distinguishes unavailable
  criteria and rejects zero substitution.
- **Criterion independence**: PASS. Data model keeps FactCheckCriterionResult and
  WritingStyleCriterionResult independent before FinalScore.
- **Explainability**: PASS. Contracts expose score composition and criterion
  evidence.
- **Integrity**: PASS. Missing fields remain nullable/omitted and no full article
  text is retained.
- **Versioning**: PASS. `pipeline_version` is required in completed analysis
  output.
- **Coverage**: PASS. `coverage` and per-criterion availability are required.
- **Limitation**: PASS. Final score is documented as operational, not factual
  probability.

## Complexity Tracking

No constitution violations or unnecessary complexity were introduced.
