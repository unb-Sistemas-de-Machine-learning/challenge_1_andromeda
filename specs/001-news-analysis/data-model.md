# Data Model: News Analysis System

## Analysis

Represents one submitted URL analysis.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | yes | Unique analysis identifier. |
| status | enum | yes | `SUCCESS`, `INVALID_URL`, `BLOCKED_INTERNAL_URL`, `NEWS_FETCH_FAILED`, `ARTICLE_EXTRACTION_FAILED`, `FACT_CHECK_API_ERROR`, `WRITING_MODEL_ERROR`, `CRITERION_UNAVAILABLE`, `RATE_LIMITED`. |
| input_url | string | yes | Original URL submitted by the user. |
| final_url | string | no | Final URL after redirects. |
| created_at | datetime | yes | Analysis start timestamp. |
| completed_at | datetime | no | Analysis completion timestamp. |
| content_hash | string | no | Hash of extracted article text; full text is not retained. |
| article | Article | no | Present when extraction succeeds. |
| criteria | CriteriaSet | yes | Current and reserved criteria. |
| final | FinalScore | yes | Final score, coverage, and effective weights. |
| pipeline_version | PipelineVersion | yes | Version of rules, models, and dependencies. |
| limitations | string[] | yes | Human-readable limitations and non-verdict warnings. |
| error | ErrorInfo | no | Present for terminal failures. |

### Validation Rules

- `input_url` must be HTTP or HTTPS.
- Full extracted article text must not be stored in `Analysis` after completion.
- `pipeline_version` is required for every completed analysis, successful or
  partial.

## Article

Prepared metadata and transient content identity for the analyzed news item.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| original_url | string | yes | Same as submitted URL unless normalized for display. |
| final_url | string | no | Final URL after redirects. |
| canonical_url | string | no | Canonical URL when discovered. |
| publisher | string | no | Vehicle/publication name if extracted. |
| title | string | no | Article title. |
| subtitle | string | no | Article subtitle. |
| author | string | no | Article author. |
| published_at | date/datetime | no | Publication date if extracted. |
| content_hash | string | yes | Hash of extracted main text. |
| extracted_character_count | integer | yes | Must be at least 1,000 for analysis. |

### Validation Rules

- Article preparation succeeds only when at least 1,000 characters of main text
  are extracted.
- Missing metadata remains missing; it must not be invented.
- Main text is transient and must be discarded after criterion execution and hash
  calculation.

## CriteriaSet

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| source_credibility | FactCheckCriterionResult | yes | Current scoring criterion, intended weight 0.60. |
| writing_style | WritingStyleCriterionResult | yes | Current scoring criterion, intended weight 0.40. |
| factual_claims | ReservedCriterionResult | yes | Future criterion, `NOT_IMPLEMENTED`. |

## FactCheckCriterionResult

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| available | boolean | yes | True only when at least one applicable normalizable review exists. |
| status | enum | yes | `EXECUTED`, `UNAVAILABLE`, `ERROR`. |
| score | number/null | yes | Normalized criterion score in 0..1, or null. |
| method | string | yes | `google_fact_check_rating`. |
| query | string | yes | Combined title plus representative excerpt when both are available. |
| reviews_count | integer | yes | Count of returned reviews preserved for traceability. |
| applicable_reviews_count | integer | yes | Count included in score aggregation. |
| reviews | FactCheckReview[] | yes | Returned review evidence. |
| error | ErrorInfo | no | Present when API call fails. |

### Validation Rules

- A review contributes to `score` only if its checked claim or review title
  matches the article title or main claim according to the documented
  conservative normalized matching rule.
- Multiple applicable normalized values are aggregated using arithmetic mean.
- Absence of applicable checks makes the criterion unavailable, not zero.
- Unmapped textual ratings are preserved and excluded from normalized score
  aggregation.

## FactCheckReview

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| claim | string | no | Checked claim text. |
| publisher_name | string | no | Organization responsible for the review. |
| publisher_site | string | no | Publisher site. |
| review_url | string | no | URL of review. |
| review_title | string | no | Title of review. |
| review_date | date/datetime | no | Review date. |
| textual_rating | string | no | Original rating text. |
| language | string | no | Returned language code. |
| applicable | boolean | yes | Whether it matches article title/main claim according to the documented matching rule. |
| normalized_value | number/null | yes | 0..1 when mapped, otherwise null. |
| raw | object | yes | Raw returned fields necessary for traceability. |

## WritingStyleCriterionResult

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| available | boolean | yes | True when model inference succeeds. |
| status | enum | yes | `EXECUTED`, `UNAVAILABLE`, `ERROR`. |
| score | number/null | yes | `writing_score` in 0..1, or null. |
| model | string | yes | `vzani/portuguese-fake-news-classifier-bertimbau-combined`. |
| model_version | string | yes | Resolved local/model revision when available. |
| prediction | WritingPrediction | no | Aggregate prediction. |
| segments_analyzed | integer | yes | Number of text segments classified. |
| segments | WritingSegmentResult[] | yes | Segment-level traceability. |
| qualitative_state | string/null | yes | `Sinal de escrita suspeito` when predicted class is `Fake`. |
| limitation | string | yes | Explains that writing signal is not a factual verdict. |
| error | ErrorInfo | no | Present when model inference fails. |

### Validation Rules

- `LABEL_0` maps to `Fake`; `LABEL_1` maps to `True`.
- If predicted class is `True`, segment `writing_score = confidence`.
- If predicted class is `Fake`, segment `writing_score = 1 - confidence`.
- Long articles are segmented and aggregate score is a text-length-weighted mean.
- `qualitative_state` must not be presented as a factual verdict.

## WritingPrediction

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| label | enum | yes | `Fake` or `True`. |
| confidence | number | yes | Classifier confidence for aggregate class. |
| writing_score | number | yes | Normalized score oriented toward `True`. |

## WritingSegmentResult

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| index | integer | yes | Zero-based or one-based index, documented consistently. |
| character_count | integer | yes | Used for weighted aggregation. |
| token_count | integer | no | Optional if tokenizer exposes it. |
| label | enum | yes | `Fake` or `True`. |
| confidence | number | yes | Classifier confidence. |
| writing_score | number | yes | Segment score oriented toward `True`. |

## ReservedCriterionResult

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| available | boolean | yes | Always false in current scope. |
| score | null | yes | Always null in current scope. |
| status | enum | yes | `NOT_IMPLEMENTED`. |
| planned_model | string | yes | `Ashg2099/xlm-roberta-factchecker`. |
| planned_flow | string[] | yes | Claim extraction, evidence retrieval, claim+evidence classification. |

## FinalScore

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| score | number/null | yes | 0..100 when any current criterion is available. |
| coverage | number | yes | 100, 60, 40, or 0 under current criteria. |
| intended_weights | object | yes | Fact-checking 0.60; writing style 0.40. |
| effective_weights | object | yes | Renormalized over available criteria. |
| formula | string | yes | Human-readable formula used. |
| limitation | string | yes | Not a probability of truth/falsity. |

### Validation Rules

- Both criteria available: `(0.60 * C + 0.40 * W) * 100`.
- Only fact-checking available: `C * 100`.
- Only writing style available: `W * 100`.
- No current criteria available: `score = null`, `coverage = 0`.
- Unavailable criteria are never substituted with zero.

## PipelineVersion

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | yes | Human-readable version identifier. |
| rules_version | string | yes | Normalization and aggregation rules. |
| fact_check_mapping_version | string | yes | Rating mapping version. |
| writing_model_name | string | yes | Hugging Face model name. |
| writing_model_revision | string | no | Model revision/hash if available. |
| dependency_versions | object | yes | Relevant dependency versions. |

## ErrorInfo

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| code | string | yes | One of the documented failure states. |
| message | string | yes | Clear user-facing or operator-facing feedback. |
| retryable | boolean | yes | Whether retry may succeed. |
| details | object | no | Safe diagnostic metadata. |

## State Transitions

```text
RECEIVED
  -> URL_REJECTED
  -> URL_BLOCKED
  -> FETCH_FAILED
  -> EXTRACTION_FAILED
  -> ANALYZING
       -> PARTIAL_RESULT
       -> SUCCESS
       -> NO_CRITERIA_AVAILABLE
  -> RATE_LIMITED
```

- `URL_REJECTED` maps to `INVALID_URL`.
- `URL_BLOCKED` maps to `BLOCKED_INTERNAL_URL`.
- `FETCH_FAILED` maps to `NEWS_FETCH_FAILED`.
- `EXTRACTION_FAILED` maps to `ARTICLE_EXTRACTION_FAILED`.
- `PARTIAL_RESULT` can still produce `SUCCESS` with reduced coverage when one
  current criterion succeeds.
