# Data Model: News Analysis System

## Analysis

Represents one submitted URL analysis.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | yes | Unique analysis identifier. |
| status | enum | yes | `SUCCESS`, `INVALID_URL`, `BLOCKED_INTERNAL_URL`, `NEWS_FETCH_FAILED`, `ARTICLE_EXTRACTION_FAILED`, `FACT_CHECK_API_ERROR`, `WRITING_MODEL_ERROR`, `CRITERION_UNAVAILABLE`, `RATE_LIMITED`. |
| input | object | yes | Original `url` and optional user-selected `claim`. |
| final_url | string | no | Final URL after redirects. |
| created_at | datetime | yes | Analysis start timestamp. |
| completed_at | datetime | no | Analysis completion timestamp. |
| content_hash | string | no | Hash of extracted article text; full text is not retained. |
| article | Article | no | Present when extraction succeeds. |
| criteria | CriteriaSet | yes | Implemented criteria. |
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
| verifiable_facts | FactCheckCriterionResult | yes | Current scoring criterion, intended weight 0.60. |
| writing_style | WritingStyleCriterionResult | yes | Current scoring criterion, intended weight 0.40. |
| credibility | object | no | Independent SCORE_FONTE; null source score means unavailable, without veto. |
| credibility_evidence | object | no | Recognition evidence, effective policy/hash, blocklist state/hash and veto reason. |
| source_credibility | HistoricalSourceCredibility | no | Read-only v4 metadata criterion; original 50/30/20 scoring is preserved. |

## FactCheckCriterionResult

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| available | boolean | yes | True only when at least one applicable normalizable review exists. |
| status | enum | yes | `EXECUTED`, `UNAVAILABLE`, `ERROR`. |
| score | number/null | yes | Normalized criterion score in 0..1, or null. |
| name | string | yes | `Checagem de fatos verificáveis`. |
| method | string | yes | `google_fact_check_claim_reviews`. |
| target_claim / claim_origin | string | no / yes | Selected claim and user or article-title/excerpt origin. |
| scope / limitation / formula | string | yes | Single-claim scope, lexical matching limits and publisher-balanced formula. |
| query | string | yes | Selected search query, after combined/fallback construction. |
| reviews_count | integer | yes | Count of returned reviews preserved for traceability. |
| applicable_reviews_count | integer | yes | Matched reviews, including those excluded for other reasons. |
| scored_reviews_count / publishers_count | integer | yes | Unique scored reviews and identified checking publishers. |
| publisher_scores | object | yes | Mean claim-rating value per checking publisher; not publisher reputation. |
| conflicting_verdicts | boolean | yes | Retained values occur both below and above 0.5. |
| search_attempts / search_truncated | array / boolean | yes | Queries attempted and pagination boundary. |
| reviews | FactCheckReview[] | yes | Returned review evidence. |
| error | ErrorInfo | no | Present when API call fails. |

The UI renders this criterion even when unavailable or absent in a payload.
Legacy `source_credibility` can be read as a compatibility input; missing new
metadata is not inferred. `publisher_scores` describes claim verdicts per agency,
not reputation. The summary shows formula and analysis ID, and distinguishes
writing-only scores from factual verification.

### Validation Rules

- Match only `Claim.text` to the selected claim. Reject numeric, negation and
  debunking-marker differences; otherwise require exact normalized equality or
  80% overlap in both directions with at least three shared meaningful tokens.
- Map only complete recognized labels; never match a rating substring.
- Exclude duplicate review URL/claim pairs and missing checking-publisher identity.
- Average ratings per publisher, then average publisher means equally.
- This is a single-claim signal, not source reputation or verification of all article facts.
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
| claimant / claim_date | string | no | Originator and date of the reviewed claim. |
| applicable | boolean | yes | Whether it matches article title/main claim according to the documented matching rule. |
| normalized_value | number/null | yes | 0..1 when mapped, otherwise null. |
| included_in_score | boolean | yes | Whether all scoring filters passed. |
| exclusion_reason / publisher_key | string | no | Filter reason and checking-publisher identity. |
| raw | object | yes | Raw returned fields necessary for traceability. |

## WritingStyleCriterionResult

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| available | boolean | yes | True when model inference succeeds. |
| status | enum | yes | `EXECUTED`, `UNAVAILABLE`, `ERROR`. |
| score | number/null | yes | `writing_score` in 0..1, or null. |
| model | string | yes | `vzani/portuguese-fake-news-classifier-bertimbau-combined`. |
| model_version | string | yes | Pinned revision `86971e56e7f5ad781cf56673df73a57375455793`. |
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
- Segment score is the softmax probability at class index 1 from actual BERTimbau inference.
- Long articles use non-overlapping windows of at most 512 tokens including special tokens, with no discarded overflow.
- Aggregate score is `sum(character_count * writing_score) / sum(character_count)`.
- Aggregate class is `True` when the unrounded mean is at least 0.5, otherwise `Fake`; confidence is that mean or its complement respectively.
- Aggregate score and prediction values are rounded to four decimal places; segment outputs preserve model probabilities.
- Loading/inference failure sets `available=false`, `status=ERROR`, no prediction, no score, zero segments, and `WRITING_MODEL_ERROR`; nullable fields may be omitted by JSON serialization.
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
| index | integer | yes | Zero-based segment index. |
| character_count | integer | yes | Character span in whitespace-normalized extracted text, derived from offsets and used for weighted aggregation. |
| token_count | integer | yes on successful inference | Actual model input token count, including special tokens; at most 512. |
| label | enum | yes | `Fake` or `True`. |
| confidence | number | yes | Classifier confidence. |
| writing_score | number | yes | Segment score oriented toward `True`. |

These per-segment values are accessible through the expandable UI section,
the response JSON and the audit record. UI scores use two decimal places,
contributions one, and displayed weights/confidence whole percentages; this
presentation precision does not replace the stored numeric values.

## FinalScore

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| score | number/null | yes | 0..100 when any current criterion is available. |
| coverage | number | yes | 100, 60, 40, or 0 under current criteria. |
| score_before_veto | number or null | no | New analyses: averaging result before the source cap. Absent from old records. |
| source_veto_applied | boolean or null | no | Whether a source veto was applied to an existing final score. |
| intended_weights | object | yes | Fact-checking 0.60; writing style 0.40. |
| effective_weights | object | yes | Renormalized over available criteria. |
| formula | string | yes | Human-readable formula used. |
| limitation | string | yes | Not a probability of truth/falsity. |

### Validation Rules

- Both criteria available: `(0.60 * F + 0.40 * W) * 100`.
  This and the renormalized cases define the pre-veto mean. An available source
  score below 20 or a confirmed blocklist match caps the final score at 35;
  completely unavailable source evidence does not. Contributions describe the
  pre-veto mean. Source evidence never creates a final score on its own.
- Only fact-checking available: `F * 100`.
- Only writing style available: `W * 100`.
- No current criteria available: `score = null`, `coverage = 0`.
- Unavailable criteria are never substituted with zero.

## PipelineVersion

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | string | yes | Human-readable version identifier. |
| rules_version | string | yes | `analysis-rules-v3-verifiable-facts`. |
| fact_check_mapping_version | string | yes | Rating mapping version. |
| writing_model_name | string | yes | Hugging Face model name. |
| writing_model_revision | string | yes | `86971e56e7f5ad781cf56673df73a57375455793`. |
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
