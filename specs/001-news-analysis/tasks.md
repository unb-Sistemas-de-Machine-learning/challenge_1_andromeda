# Tasks: News Analysis System

**Input**: Design documents from `specs/001-news-analysis/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Included because the implementation plan and quickstart define contract, integration, and unit validation targets.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and does not depend on incomplete tasks.
- **[Story]**: User story label from `spec.md` (`US1`, `US2`, `US3`, `US4`).
- Every task includes exact file paths.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize the Python service, package layout, dependency metadata, and test harness.

- [X] T001 Create Python package directories from `plan.md` in `src/news_analysis/` and test directories in `tests/`
- [X] T002 Create `pyproject.toml` with Python 3.11, FastAPI, Pydantic, httpx, trafilatura, transformers, torch, pytest, respx, uvicorn, and dev extras
- [X] T003 [P] Create package marker files in `src/news_analysis/__init__.py`, `src/news_analysis/api/__init__.py`, `src/news_analysis/article/__init__.py`, `src/news_analysis/criteria/__init__.py`, `src/news_analysis/pipeline/__init__.py`, and `src/news_analysis/storage/__init__.py`
- [X] T004 [P] Configure pytest defaults and import path in `pyproject.toml`
- [X] T005 [P] Create `.env.example` documenting `FACTCHECK_API_KEY`, `NEWS_ANALYSIS_DB_PATH`, and optional model cache settings
- [X] T006 [P] Create `src/news_analysis/config.py` for environment-driven settings, including `FACTCHECK_API_KEY`, SQLite path, fetch limits, and rate limit values

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared schemas, storage, errors, and pipeline primitives required by every user story.

**Critical**: No user story work can begin until this phase is complete.

- [X] T007 Define status/error enums in `src/news_analysis/pipeline/errors.py` for `SUCCESS`, `INVALID_URL`, `BLOCKED_INTERNAL_URL`, `NEWS_FETCH_FAILED`, `ARTICLE_EXTRACTION_FAILED`, `FACT_CHECK_API_ERROR`, `WRITING_MODEL_ERROR`, `CRITERION_UNAVAILABLE`, and `RATE_LIMITED`
- [X] T008 [P] Define Pydantic API schemas matching `contracts/openapi.yaml` in `src/news_analysis/api/schemas.py`
- [X] T009 [P] Define domain dataclasses or Pydantic models for `Analysis`, `Article`, `CriteriaSet`, `FactCheckCriterionResult`, `FactCheckReview`, `WritingStyleCriterionResult`, `WritingPrediction`, `WritingSegmentResult`, `ReservedCriterionResult`, `FinalScore`, `PipelineVersion`, and `ErrorInfo` in `src/news_analysis/pipeline/models.py`
- [X] T010 [P] Implement pipeline version constants in `src/news_analysis/pipeline/version.py` with `id`, `rules_version`, `fact_check_mapping_version`, `writing_model_name`, `writing_model_revision`, and `dependency_versions`
- [X] T011 Implement SQLite schema creation in `src/news_analysis/storage/schema.py` for analysis records, criterion payloads, raw external responses, model outputs, final score, coverage, and pipeline version
- [X] T012 Implement audit repository in `src/news_analysis/storage/audit_repository.py` that saves and retrieves analyses without retaining full extracted article text
- [X] T013 [P] Implement final score and coverage utilities in `src/news_analysis/pipeline/aggregation.py` for `(0.60 * C + 0.40 * W) * 100`, `C * 100`, `W * 100`, and `score = null` when no current criteria are available
- [X] T014 [P] Implement coverage utility in `src/news_analysis/pipeline/coverage.py` returning `100`, `60`, `40`, or `0` based on available current criteria
- [X] T015 [P] Create shared test fixtures in `tests/conftest.py` for temporary SQLite database, sample article metadata, sample fact-check responses, and deterministic writing classifier doubles
- [X] T016 [P] Create contract test skeleton loading `specs/001-news-analysis/contracts/openapi.yaml` in `tests/contract/test_openapi_contract.py`

**Checkpoint**: Foundation ready; user story implementation can begin.

---

## Phase 3: User Story 1 - Analyze a News URL (Priority: P1) MVP

**Goal**: A user submits one valid news URL and receives a structured analysis result with article metadata, current criteria, final score or null score, coverage, and explanations.

**Independent Test**: Submit a valid HTTP/HTTPS extractable news URL using mocked external services and verify the response includes article metadata, criterion availability, normalized results, final index, coverage, limitations, and no truth-probability claim.

### Tests for User Story 1

- [X] T017 [P] [US1] Add contract test for `POST /analyses` success and error response shapes in `tests/contract/test_create_analysis_contract.py`
- [X] T018 [P] [US1] Add unit tests for HTTP/HTTPS validation and unsupported scheme handling in `tests/unit/test_url_validation.py`
- [X] T019 [P] [US1] Add unit tests for blocked localhost, loopback, private range, link-local, and cloud metadata URLs in `tests/unit/test_url_safety.py`
- [X] T020 [P] [US1] Add unit tests for 10-second timeout, 5 MB download cap, and 5 redirect cap behavior in `tests/unit/test_article_fetcher_limits.py`
- [X] T021 [P] [US1] Add unit tests for article extraction threshold requiring at least 1,000 main-text characters in `tests/unit/test_article_extractor.py`
- [X] T022 [P] [US1] Add integration test for successful `POST /analyses` with mocked article page, mocked Fact Check response, and mocked writing classifier in `tests/integration/test_analyze_url_success.py`
- [X] T023 [P] [US1] Add integration tests for `INVALID_URL`, `BLOCKED_INTERNAL_URL`, `NEWS_FETCH_FAILED`, and `ARTICLE_EXTRACTION_FAILED` in `tests/integration/test_analyze_url_failures.py`
- [X] T071 [P] [US1] Add integration test for more than 10 analysis requests per same `user_id` within one minute returning `RATE_LIMITED` and HTTP 429 in `tests/integration/test_rate_limit.py`

### Implementation for User Story 1

- [X] T024 [P] [US1] Implement URL validation in `src/news_analysis/article/safety.py` for HTTP/HTTPS only and `INVALID_URL`
- [X] T025 [US1] Implement DNS/IP safety checks in `src/news_analysis/article/safety.py` blocking localhost, loopback, private network ranges, link-local addresses, and cloud metadata addresses with `BLOCKED_INTERNAL_URL`
- [X] T026 [US1] Implement streaming article fetcher in `src/news_analysis/article/fetcher.py` with 10-second timeout, 5 MB maximum downloaded content, and 5 redirect maximum
- [X] T027 [P] [US1] Implement trafilatura-based article extraction in `src/news_analysis/article/extractor.py` preserving original URL, final URL, canonical URL, publisher, title, subtitle, author, publication date, content hash, and extracted character count
- [X] T028 [US1] Enforce `ARTICLE_EXTRACTION_FAILED` when fewer than 1,000 characters of main article text are extracted in `src/news_analysis/article/extractor.py`
- [X] T029 [P] [US1] Implement initial Fact Check Tools client in `src/news_analysis/criteria/fact_check.py` using `claims.search`, `FACTCHECK_API_KEY`, and a combined title plus representative excerpt query
- [X] T030 [P] [US1] Implement rating normalization mapping in `src/news_analysis/criteria/rating_normalization.py` for recognized textual ratings into 0..1 values and unmapped ratings as null
- [X] T031 [P] [US1] Implement writing classifier wrapper in `src/news_analysis/criteria/writing_style.py` mapping `LABEL_0` to `Fake`, `LABEL_1` to `True`, and confidence to `writing_score`
- [X] T032 [US1] Implement long-text segmentation and text-length-weighted `writing_score` aggregation in `src/news_analysis/criteria/writing_style.py`
- [X] T033 [US1] Implement analysis orchestration in `src/news_analysis/pipeline/analyzer.py` connecting URL safety, fetch, extraction, fact-checking, writing-style classification, aggregation, coverage, limitations, and audit save
- [X] T034 [P] [US1] Implement FastAPI dependencies for settings, repository, and analyzer in `src/news_analysis/api/dependencies.py`
- [X] T035 [US1] Implement `POST /analyses` endpoint in `src/news_analysis/api/app.py` returning `AnalysisResponse` and mapped HTTP status codes
- [X] T072 [US1] Implement per-user rate limiting for `POST /analyses` in `src/news_analysis/api/app.py` or a dedicated API dependency, enforcing 10 accepted analysis requests per `user_id` per minute and returning `RATE_LIMITED` with clear feedback
- [X] T036 [US1] Ensure response limitations in `src/news_analysis/pipeline/analyzer.py` state that final scores and classifier labels are not probabilities or factual verdicts
- [X] T037 [US1] Ensure no full extracted article text is returned by `src/news_analysis/api/schemas.py` or persisted by `src/news_analysis/storage/audit_repository.py`

**Checkpoint**: User Story 1 is functional as the MVP.

---

## Phase 4: User Story 2 - Understand Criterion Contributions (Priority: P2)

**Goal**: A reviewer can audit how each criterion contributed to the final index and verify that unavailable criteria did not silently count as zero.

**Independent Test**: Run analyses for both criteria available, fact-check-only, writing-only, and no-criteria cases; verify weights, coverage, formula, normalized values, contribution, and evidence are visible and correct.

### Tests for User Story 2

- [X] T038 [P] [US2] Add unit tests for final score formulas and coverage values in `tests/unit/test_aggregation.py`
- [X] T039 [P] [US2] Add unit tests for arithmetic mean of multiple applicable normalized fact-check ratings in `tests/unit/test_fact_check_aggregation.py`
- [X] T040 [P] [US2] Add unit tests preserving but excluding fact-check results that do not clearly match article title or main claim in `tests/unit/test_fact_check_applicability.py`
- [X] T041 [P] [US2] Add unit tests for unmapped textual fact-check ratings remaining original and unnormalized in `tests/unit/test_rating_normalization.py`
- [X] T042 [P] [US2] Add integration test for partial criterion availability and renormalized weights in `tests/integration/test_partial_criteria.py`

### Implementation for User Story 2

- [X] T043 [US2] Implement documented conservative fact-check applicability filtering in `src/news_analysis/criteria/fact_check.py` where a review contributes only when the checked claim or review title matches the article title or main claim according to the normalized matching rule
- [X] T044 [US2] Preserve non-applicable Fact Check Tools results for traceability while excluding them from score aggregation in `src/news_analysis/criteria/fact_check.py`
- [X] T045 [US2] Implement fact-check criterion unavailable state when no applicable normalizable review exists in `src/news_analysis/criteria/fact_check.py`
- [X] T046 [US2] Extend aggregation output in `src/news_analysis/pipeline/aggregation.py` with intended weights, effective weights, formula string, and contribution details
- [X] T047 [US2] Extend response schema mapping in `src/news_analysis/api/schemas.py` to expose criterion original result, normalized result, method/model, weight, contribution, and supporting evidence
- [X] T048 [US2] Add criterion coverage explanations to `src/news_analysis/pipeline/analyzer.py` for 100, 60, 40, and 0 percent cases

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Preserve Audit Trail (Priority: P3)

**Goal**: Maintainers and auditors can retrieve stored analysis records with enough information to reconstruct the process without storing full article text.

**Independent Test**: Complete an analysis, retrieve it by id, and verify input URL, final URL, timestamp, content hash, metadata, raw external responses, original model outputs, normalized scores, weights, final score, coverage, pipeline version, and model versions are present while full text is absent.

### Tests for User Story 3

- [X] T049 [P] [US3] Add repository tests for saving and retrieving audit records without full extracted article text in `tests/unit/test_audit_repository.py`
- [X] T050 [P] [US3] Add contract test for `GET /analyses/{analysis_id}` success and 404 responses in `tests/contract/test_get_analysis_contract.py`
- [X] T051 [P] [US3] Add integration test for completing analysis then retrieving stored audit record by id in `tests/integration/test_analysis_audit_retrieval.py`
- [X] T052 [P] [US3] Add unit tests requiring `pipeline_version` and model version data on completed analyses in `tests/unit/test_pipeline_version.py`
- [X] T073 [P] [US3] Add unit tests requiring the pipeline version identifier to change when rules version, rating mapping version, intended weights, model revision, or dependency versions change in `tests/unit/test_pipeline_version.py`

### Implementation for User Story 3

- [X] T053 [US3] Complete SQLite persistence in `src/news_analysis/storage/audit_repository.py` for Analysis, Article metadata, CriteriaSet, FactCheckReview raw payloads, WritingPrediction, WritingSegmentResult, FinalScore, PipelineVersion, and ErrorInfo
- [X] T054 [US3] Implement `GET /analyses/{analysis_id}` endpoint in `src/news_analysis/api/app.py` returning stored `AnalysisResponse` or 404 `ErrorResponse`
- [X] T055 [US3] Record raw Fact Check Tools responses and original model outputs in `src/news_analysis/pipeline/analyzer.py` before normalization while preserving missing fields as missing
- [X] T056 [US3] Attach pipeline version and dependency versions to every completed or partial analysis in `src/news_analysis/pipeline/analyzer.py`
- [X] T057 [US3] Add audit-safe diagnostic details in `src/news_analysis/pipeline/errors.py` and `src/news_analysis/storage/audit_repository.py` without secrets or full article text
- [X] T074 [US3] Implement deterministic pipeline version identifier derivation in `src/news_analysis/pipeline/version.py` from rules version, rating mapping version, intended weights, writing model revision, and dependency versions

**Checkpoint**: User Stories 1, 2, and 3 are independently functional.

---

## Phase 6: User Story 4 - Reserve Future Factual-Claims Criterion (Priority: P4)

**Goal**: Every result communicates the planned factual-claims criterion without affecting current scoring or coverage.

**Independent Test**: Inspect any analysis result and verify `factual_claims.available = false`, `score = null`, `status = NOT_IMPLEMENTED`, planned model is `Ashg2099/xlm-roberta-factchecker`, and current score/coverage ignore it.

### Tests for User Story 4

- [X] T058 [P] [US4] Add unit tests for reserved factual-claims criterion payload in `tests/unit/test_reserved_factual_claims.py`
- [X] T059 [P] [US4] Add integration test proving reserved factual-claims criterion does not affect final score or coverage in `tests/integration/test_reserved_criterion_exclusion.py`

### Implementation for User Story 4

- [X] T060 [US4] Implement reserved factual-claims criterion factory in `src/news_analysis/criteria/factual_claims.py` with `available=false`, `score=null`, `status=NOT_IMPLEMENTED`, planned flow, and planned model `Ashg2099/xlm-roberta-factchecker`
- [X] T061 [US4] Integrate reserved factual-claims result into `CriteriaSet` assembly in `src/news_analysis/pipeline/analyzer.py`
- [X] T062 [US4] Ensure `src/news_analysis/pipeline/aggregation.py` excludes reserved factual-claims criterion from effective weights, final score, and coverage calculations
- [X] T063 [US4] Expose reserved criterion fields in `src/news_analysis/api/schemas.py` according to `specs/001-news-analysis/contracts/openapi.yaml`

**Checkpoint**: All user stories are independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation, security hardening, and cleanup across stories.

- [X] T064 [P] Run OpenAPI schema comparison between FastAPI generated schema and `specs/001-news-analysis/contracts/openapi.yaml` in `tests/contract/test_openapi_contract.py`
- [X] T065 [P] Add README usage snippet for running the service, setting `FACTCHECK_API_KEY`, and calling `POST /analyses` in `README.md`
- [X] T066 [P] Add feature documentation link and validation summary in `docs/index.md`
- [X] T067 Run quickstart validation scenarios from `specs/001-news-analysis/quickstart.md` and record any deviations in `specs/001-news-analysis/quickstart.md`
- [X] T068 Run full test suite with `pytest tests/unit tests/contract tests/integration` and fix failures in affected files
- [X] T069 Review all output messages in `src/news_analysis/` to ensure no final score or classifier output is presented as a probability of truth or falsity
- [X] T070 Review secret handling in `src/news_analysis/config.py`, `src/news_analysis/criteria/fact_check.py`, and tests to ensure API keys are never logged or persisted

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies; can start immediately.
- **Phase 2 Foundational**: Depends on Phase 1; blocks all user stories.
- **Phase 3 US1 MVP**: Depends on Phase 2.
- **Phase 4 US2**: Depends on Phase 2; can start after core models and analyzer interfaces are stable, but validates best after US1.
- **Phase 5 US3**: Depends on Phase 2; can start after audit repository interfaces exist, but validates best after US1.
- **Phase 6 US4**: Depends on Phase 2; can be implemented in parallel with US2/US3 once `CriteriaSet` exists.
- **Phase 7 Polish**: Depends on selected user stories being complete.

### User Story Dependencies

- **US1 Analyze a News URL**: MVP; no dependency on other user stories after foundation.
- **US2 Understand Criterion Contributions**: Builds on the same criterion outputs as US1 but remains independently testable with mocked criteria.
- **US3 Preserve Audit Trail**: Builds on Analysis and storage foundation; independently testable by saving/retrieving fixture analyses.
- **US4 Reserve Future Factual-Claims Criterion**: Independent reserved payload and aggregation exclusion after shared models exist.

### Parallel Opportunities

- T003, T004, T005, and T006 can run in parallel after T001.
- T008, T009, T010, T013, T014, T015, and T016 can run in parallel after T007.
- US1 test tasks T017-T023 and T071 can run in parallel.
- US1 criterion tasks T029-T032 can run in parallel after foundational models exist.
- US2 test tasks T038-T042 can run in parallel.
- US3 test tasks T049-T052 and T073 can run in parallel.
- US4 test tasks T058-T059 can run in parallel.
- Polish documentation tasks T065-T066 can run in parallel with contract comparison T064.

---

## Parallel Example: User Story 1

```text
Task: "T017 [P] [US1] Add contract test for POST /analyses success and error response shapes in tests/contract/test_create_analysis_contract.py"
Task: "T018 [P] [US1] Add unit tests for HTTP/HTTPS validation and unsupported scheme handling in tests/unit/test_url_validation.py"
Task: "T019 [P] [US1] Add unit tests for blocked localhost, loopback, private range, link-local, and cloud metadata URLs in tests/unit/test_url_safety.py"
Task: "T020 [P] [US1] Add unit tests for 10-second timeout, 5 MB download cap, and 5 redirect cap behavior in tests/unit/test_article_fetcher_limits.py"
Task: "T021 [P] [US1] Add unit tests for article extraction threshold requiring at least 1,000 main-text characters in tests/unit/test_article_extractor.py"
```

## Parallel Example: User Story 2

```text
Task: "T038 [P] [US2] Add unit tests for final score formulas and coverage values in tests/unit/test_aggregation.py"
Task: "T039 [P] [US2] Add unit tests for arithmetic mean of multiple applicable normalized fact-check ratings in tests/unit/test_fact_check_aggregation.py"
Task: "T040 [P] [US2] Add unit tests preserving but excluding fact-check results that do not clearly match article title or main claim in tests/unit/test_fact_check_applicability.py"
Task: "T041 [P] [US2] Add unit tests for unmapped textual fact-check ratings remaining original and unnormalized in tests/unit/test_rating_normalization.py"
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 only.
3. Validate `POST /analyses` with mocked article fetching, mocked Fact Check Tools responses, mocked writing classifier, and SQLite audit storage.
4. Demonstrate that the result has score, coverage, limitations, and no factual verdict language.

### Incremental Delivery

1. Add US1 for end-to-end analysis.
2. Add US2 to deepen score composition and explainability.
3. Add US3 to make audit retrieval and persistence complete.
4. Add US4 to expose the future factual-claims criterion without changing score semantics.
5. Run Phase 7 validation before considering implementation complete.

### Quality Gates

- Every criterion output must preserve source/model, original result, normalized value, and contribution.
- Unavailable criteria must not become zero.
- Full extracted article text must not be persisted.
- Pipeline version must appear on completed or partial analyses.
- Final score and writing labels must never be presented as factual truth/falsity probabilities.
