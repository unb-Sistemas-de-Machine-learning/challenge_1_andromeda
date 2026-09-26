# Feature Specification: News Analysis System

**Feature Branch**: `001-news-analysis`

**Created**: 2026-09-26

**Status**: Draft

**Input**: User description: "Sistema de análise de notícias por URL que produz um índice de confiabilidade transparente, rastreável e explicável, usando sinal de fact-checking publicado, classificador de características de escrita e reserva de um terceiro critério factual para implementação futura."

## Clarifications

### Session 2026-09-26

- Q: Como o sistema deve agregar múltiplas verificações de fact-checking normalizáveis encontradas para a mesma notícia? → A: Média aritmética dos valores normalizados de todas as verificações aplicáveis.
- Q: Como o sistema deve agregar os resultados quando uma notícia longa for dividida em múltiplos segmentos para o classificador de escrita? → A: Média dos `writing_score` dos segmentos ponderada pelo tamanho textual de cada segmento.
- Q: O sistema deve bloquear URLs que apontem para redes privadas, locais ou endereços internos? → A: Sim; bloquear localhost, IPs privados, loopback, link-local e metadados de nuvem, com feedback claro de que a URL foi bloqueada por segurança.
- Q: Quais limites mínimos de busca de notícia devem ser aceitos como regra de produto para evitar análises travadas ou abusivas? → A: Timeout de 10 segundos, máximo de 5 MB baixados e máximo de 5 redirecionamentos.
- Q: Por quanto tempo o sistema deve preservar o texto extraído da notícia no registro de auditoria? → A: Não preservar texto completo; guardar apenas hash, metadados e resultados.
- Q: Qual deve ser o mínimo de texto extraído para considerar que a notícia foi preparada com sucesso? → A: Pelo menos 1.000 caracteres de texto principal extraído.
- Q: Qual consulta deve ser usada primeiro no fact-checking quando houver título e texto principal disponíveis? → A: Sempre combinar título e trecho representativo em uma única consulta.
- Q: Quando a Google Fact Check Tools API encontrar resultados, como o sistema deve decidir quais verificações são aplicáveis à notícia analisada? → A: Aplicar apenas verificações cuja alegação ou título tenha correspondência clara com o título ou alegação principal da notícia.
- Q: Quando a escrita for classificada como `Fake`, qual estado qualitativo deve aparecer junto do índice para evitar que o usuário confunda o score com veredito factual? → A: "Sinal de escrita suspeito", deixando claro que não é veredito factual.
- Q: Qual limite inicial de requisições por usuário deve ser adotado para evitar uso abusivo da análise? → A: 10 análises por minuto por usuário.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Analyze a News URL (Priority: P1)

As a person who receives a political news link, I want to submit the URL and
receive a reliability index with the evidence used, so that I can decide whether
the content deserves further trust or verification before sharing it.

**Why this priority**: This is the core user value: a usable analysis from a
single news URL with enough transparency to avoid treating the score as a
truth verdict.

**Independent Test**: Can be fully tested by submitting a valid HTTP or HTTPS
news URL whose article content can be extracted and verifying that the system
returns article metadata, executed criteria, normalized criterion results, final
index, coverage, and explanations.

**Acceptance Scenarios**:

1. **Given** a valid HTTP or HTTPS URL for an extractable news article, **When**
   the analysis is initiated, **Then** the system attempts to fetch and prepare
   the article content.
2. **Given** the article content is extractable and at least one criterion can be
   executed, **When** the analysis completes, **Then** the system returns a
   structured result with criterion availability, criterion scores, final score,
   coverage, and traceability information.
3. **Given** any final score is produced, **When** the result is displayed or
   returned, **Then** the system does not present the score as a probability that
   the news is true or false.

---

### User Story 2 - Understand Criterion Contributions (Priority: P2)

As a reviewer or project evaluator, I want to see how each available criterion
contributed to the final index, so that I can audit whether the score follows
the documented rules and does not hide missing evidence.

**Why this priority**: The project constitution requires transparency,
independent criteria, coverage reporting, and explainability for every score.

**Independent Test**: Can be tested by using analysis cases where both criteria
are available, only fact-checking is available, only writing analysis is
available, and no criteria are available, then verifying that the final score and
coverage follow the documented aggregation rules.

**Acceptance Scenarios**:

1. **Given** both current criteria are available, **When** the final index is
   calculated, **Then** the fact-checking criterion contributes 60% and the
   writing-style criterion contributes 40%.
2. **Given** only one current criterion is available, **When** the final index is
   calculated, **Then** the system renormalizes weights over the available
   criterion and does not substitute zero for the missing criterion.
3. **Given** no current criterion produces a result, **When** the analysis
   completes, **Then** the final index is unavailable and coverage is 0%.

---

### User Story 3 - Preserve Audit Trail (Priority: P3)

As a maintainer or auditor, I want each analysis to record the inputs, sources,
model outputs, normalization rules, weights, and pipeline version used, so that
the result can be reconstructed later.

**Why this priority**: Rastreability is necessary for credible analysis,
debugging, academic evaluation, and future comparison after pipeline changes.

**Independent Test**: Can be tested by completing an analysis and verifying that
the result contains an analysis identifier, source URL details, article metadata,
raw external-source results where applicable, original model result, normalized
scores, weights, coverage, final score, and pipeline/model versions.

**Acceptance Scenarios**:

1. **Given** an analysis has completed, **When** its audit record is inspected,
   **Then** the record identifies the input URL, final URL, analysis timestamp,
   content hash, extracted metadata, criterion outputs, normalized scores,
   weights, final index, coverage, pipeline version, and model versions where
   available.
2. **Given** a criterion cannot be executed, **When** the result is inspected,
   **Then** the affected criterion is marked unavailable with an identifiable
   reason and the remaining criteria remain auditable.

---

### User Story 4 - Reserve Future Factual-Claims Criterion (Priority: P4)

As a project team member, I want the future factual-claims criterion represented
without affecting the current index, so that the system can communicate planned
scope without changing current score semantics.

**Why this priority**: The future criterion is important for roadmap clarity but
must not reduce current coverage or alter current scoring before it is
implemented.

**Independent Test**: Can be tested by inspecting any current result and
verifying that the factual-claims criterion is reported as not implemented,
has no score, and is excluded from current scoring and coverage.

**Acceptance Scenarios**:

1. **Given** the third criterion is not implemented, **When** any analysis result
   is produced, **Then** the factual-claims criterion is marked `NOT_IMPLEMENTED`
   and does not participate in the final index.
2. **Given** only the two current criteria are considered, **When** coverage is
   calculated, **Then** the reserved criterion does not reduce coverage.

### Edge Cases

- The URL is malformed, missing a scheme, or uses a scheme other than HTTP or
  HTTPS.
- The URL resolves to localhost, loopback, private network ranges, link-local
  addresses, or cloud metadata addresses and must be blocked with clear security
  feedback.
- The URL is valid but cannot be reached, exceeds a 10-second fetch timeout,
  exceeds 5 redirects, or returns more than 5 MB of content.
- The page is reachable but fewer than 1,000 characters of main article text can
  be extracted for analysis.
- Article metadata such as author, subtitle, publication date, or canonical URL
  is missing.
- The fact-checking source returns no applicable checks.
- The fact-checking source returns textual ratings that have no configured
  normalized mapping.
- The fact-checking source returns checks that do not clearly match the article
  title or main claim and therefore must not be treated as applicable.
- The fact-checking source is unavailable or returns an error while the writing
  criterion can still run.
- The writing classifier cannot process the text, or only part of the text can
  be segmented and classified.
- The article text exceeds the classifier input limit and must be analyzed in
  multiple segments.
- Both current criteria are unavailable, leaving the final score unavailable.
- External page content attempts to influence internal analysis rules or expose
  secrets.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a single HTTP or HTTPS news URL as the primary
  input for an analysis.
- **FR-002**: System MUST reject invalid URLs and URLs with unsupported schemes
  with an `INVALID_URL` failure and no final index.
- **FR-003**: System MUST attempt to fetch the reachable content for a valid URL
  while treating the URL and remote content as untrusted input.
- **FR-004**: System MUST block URLs that resolve to localhost, loopback,
  private network ranges, link-local addresses, or cloud metadata addresses, and
  MUST provide clear feedback that the URL was blocked for security.
- **FR-005**: System MUST identify and extract the main article content when at
  least 1,000 characters of main article text are available.
- **FR-006**: System MUST preserve available article metadata, including original
  URL, final URL after redirects, canonical URL, publisher, title, subtitle,
  author, publication date, extracted character count, and content hash. The
  extracted main text MUST be used only transiently during analysis and MUST NOT
  be returned or persisted after criterion execution.
- **FR-007**: System MUST NOT invent article metadata, sources, evidence,
  fact-check reviews, model outputs, or analysis results.
- **FR-008**: System MUST fail with `ARTICLE_EXTRACTION_FAILED` when fewer than
  1,000 characters of main article text can be extracted for current analysis.
- **FR-009**: System MUST execute a fact-checking criterion that searches the
  Google Fact Check Tools API for published fact checks related to the article's
  claims or representative text.
- **FR-010**: System MUST preserve each fact-check result found, including the
  checked claim, checking organization, organization site, review URL, review
  title, review date, textual rating, language, and other relevant returned
  fields when available.
- **FR-011**: System MUST use one combined query containing the article title and
  a representative excerpt of the main text when both are available for
  fact-checking lookup.
- **FR-012**: System MUST treat a fact-check result as applicable only when the
  checked claim or review title clearly matches the article title or main claim.
- **FR-012A**: System MUST determine fact-check applicability using a documented
  conservative matching rule: normalize article title or main claim and returned
  checked claim or review title, compare meaningful tokens after stopword
  removal, and mark a review applicable only when the overlap or configured
  matcher indicates the same central claim.
- **FR-013**: System MUST normalize recognized fact-check ratings into values
  between 0 and 1 using documented mapping rules.
- **FR-014**: System MUST preserve unmapped textual fact-check ratings without
  converting them arbitrarily.
- **FR-015**: System MUST aggregate multiple applicable normalized fact-check
  ratings using the arithmetic mean while preserving each individual review and
  normalized value.
- **FR-016**: System MUST mark the fact-checking criterion unavailable when no
  applicable fact checks or no normalizable fact-check result is available.
- **FR-017**: System MUST NOT interpret absence of fact-check results as evidence
  that the article is true.
- **FR-018**: System MUST execute a writing-style criterion using the
  `vzani/portuguese-fake-news-classifier-bertimbau-combined` Portuguese
  fake-news writing classifier when article text is available.
- **FR-019**: System MUST preserve the writing classifier's original predicted
  class, associated confidence, number of analyzed segments, and the qualitative
  state "Sinal de escrita suspeito" when the predicted class is `Fake`.
- **FR-020**: System MUST treat classifier confidence as confidence in the
  classifier output, not as a calibrated probability that the article is true or
  false, and MUST explicitly state that "Sinal de escrita suspeito" is a
  writing-style signal rather than a factual verdict.
- **FR-021**: System MUST normalize writing classifier output into a
  `writing_score` between 0 and 1 oriented toward the `True` class.
- **FR-022**: System MUST segment long article text when it exceeds the current
  classifier input limit, calculate one `writing_score` per segment, aggregate
  segment scores using a text-length-weighted mean, and record the number of
  segments analyzed.
- **FR-023**: System MUST calculate the final index on a 0 to 100 scale when at
  least one current criterion is available.
- **FR-024**: System MUST use initial intended weights of 60% for fact-checking
  and 40% for writing style when both criteria are available.
- **FR-025**: System MUST renormalize weights across available criteria when one
  current criterion is unavailable.
- **FR-026**: System MUST NOT use zero as a substitute for an unavailable
  criterion.
- **FR-027**: System MUST return a `null` final score when no current criterion
  is available.
- **FR-028**: System MUST report analysis coverage as the share of current
  intended evaluation that was actually executed: 100% when both current
  criteria are available, 60% when only fact-checking is available, 40% when only
  writing style is available, and 0% when neither is available.
- **FR-029**: System MUST report, for each criterion, whether it was executed,
  source or model used, original result, normalized result, contribution to the
  final index, and supporting information.
- **FR-030**: System MUST include the reserved factual-claims criterion in the
  result as `NOT_IMPLEMENTED` while it remains outside current scope.
- **FR-031**: System MUST document the reserved factual-claims criterion as a
  future flow that extracts claims, retrieves evidence, and classifies
  claim-evidence pairs with the planned `Ashg2099/xlm-roberta-factchecker`
  model.
- **FR-032**: System MUST exclude the reserved factual-claims criterion from the
  current final index and coverage calculations.
- **FR-033**: System MUST assign a unique identifier to each analysis.
- **FR-034**: System MUST preserve enough information to reconstruct an analysis,
  including input URL, final URL, analysis time, content hash, metadata, raw
  external-source responses when applicable, original model outputs, normalized
  scores, weights, final index, coverage, pipeline version, and model versions.
- **FR-035**: System MUST distinguish at least these states: `INVALID_URL`,
  `BLOCKED_INTERNAL_URL`, `NEWS_FETCH_FAILED`, `ARTICLE_EXTRACTION_FAILED`,
  `FACT_CHECK_API_ERROR`, `WRITING_MODEL_ERROR`, and `CRITERION_UNAVAILABLE`.
- **FR-036**: System MUST allow one criterion to fail without invalidating the
  whole analysis when at least one other current criterion can produce a result.
- **FR-037**: System MUST protect credentials and other secrets from being stored
  in source content or exposed through analyzed remote content.
- **FR-038**: System MUST limit unsafe or abusive analysis inputs to a
  10-second fetch timeout, a maximum of 5 MB downloaded content, a maximum of 5
  redirects, and a maximum of 10 analyses per minute per user.
- **FR-039**: System MUST prevent external article content from changing internal
  analysis rules, weights, criteria, credentials, or output semantics.
- **FR-040**: System MUST version changes to models, weights, normalization
  rules, aggregation rules, or relevant dependencies so results remain
  interpretable over time.
- **FR-041**: System MUST present the final index as an operational combination
  of executed criteria, not as a probability that the news is true or false.
- **FR-042**: System MUST NOT preserve the full extracted article text in the
  audit record after analysis completion; only the content hash, metadata,
  criterion outputs, and analysis results may be retained.

### Key Entities *(include if feature involves data)*

- **Analysis**: A single execution for one submitted URL. Key attributes include
  identifier, status, input URL, final URL, analysis timestamp, content hash,
  pipeline version, final score, coverage, and error state if applicable.
- **Article**: The prepared news content. Key attributes include original URL,
  final URL, canonical URL, publisher, title, subtitle, author, publication date,
  content hash, and transient extracted text used during analysis but not
  retained in the audit record.
- **Criterion Result**: The outcome of one analysis criterion. Key attributes
  include criterion name, availability, execution status, source or model,
  original result, normalized score, weight, contribution, and supporting
  evidence.
- **Fact-Check Review**: A published fact-check item associated with the article
  or its claims. Key attributes include checked claim, organization, organization
  site, review URL, review title, review date, textual rating, language, raw
  fields, and normalized value when mapping exists.
- **Writing Classification**: The writing-style classifier outcome. Key
  attributes include predicted class, confidence, normalized writing score,
  segment-level writing scores when segmentation occurs, segment text lengths,
  segments analyzed, and model version.
- **Pipeline Version**: The identifiable version of the analysis rules and
  dependencies that produced the result. Key attributes include models, weights,
  normalization rules, aggregation rules, and relevant dependency versions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For 100% of successful analyses with at least one available
  current criterion, the result includes a final index between 0 and 100,
  coverage percentage, and per-criterion contribution details.
- **SC-002**: For 100% of analyses where no current criterion is available, the
  result leaves the final score unavailable and reports 0% coverage.
- **SC-003**: For 100% of URLs blocked because they resolve to internal or
  restricted network destinations, the system returns `BLOCKED_INTERNAL_URL`,
  produces no final index, and clearly explains that the URL was blocked for
  security.
- **SC-004**: For 100% of fetch attempts that exceed 10 seconds, 5 MB of
  downloaded content, or 5 redirects, the system stops the fetch, returns an
  identifiable failure state, and produces no analysis from incomplete or unsafe
  content.
- **SC-005**: For 100% of users who exceed 10 analysis requests in one minute,
  the system rejects additional requests during that minute with clear feedback
  that the rate limit was reached.
- **SC-006**: For 100% of reachable pages with fewer than 1,000 extracted
  characters of main article text, the system returns `ARTICLE_EXTRACTION_FAILED`
  and produces no criterion scores or final index.
- **SC-007**: In a validation set covering both-criteria, fact-check-only,
  writing-only, and no-criteria cases, 100% of final score calculations follow
  the documented weighting and renormalization rules.
- **SC-008**: For 100% of fact-checking lookups where both title and main text
  are available, the initial lookup uses one combined query containing the title
  and a representative excerpt of the main text.
- **SC-009**: For 100% of fact-check results that do not clearly match the
  article title or main claim, the result is preserved for traceability but
  excluded from fact-checking score aggregation.
- **SC-010**: For 100% of fact-check results with recognized ratings, normalized
  values fall within the 0 to 1 range and preserve the original rating text.
- **SC-011**: For 100% of unmapped fact-check ratings, the original rating is
  preserved and no arbitrary normalized value is assigned.
- **SC-012**: For 100% of analyses with multiple applicable normalizable
  fact-check reviews, the fact-checking criterion score equals the arithmetic
  mean of the individual normalized review values.
- **SC-013**: For 100% of writing-style analyses, the result preserves the
  predicted class, classifier confidence, normalized writing score, segment
  count, and displays "Sinal de escrita suspeito" with a non-verdict explanation
  when the predicted class is `Fake`.
- **SC-014**: For 100% of long articles that exceed classifier input limits, the
  result records that segmentation occurred, reports the number of analyzed
  segments, and calculates the final writing score as the text-length-weighted
  mean of segment writing scores.
- **SC-015**: For 100% of completed analyses, the audit record includes an
  analysis identifier, input URL, final URL when available, timestamp, pipeline
  version, executed criteria, criterion availability, normalized scores, weights,
  final score, coverage, and content hash without retaining the full extracted
  article text.
- **SC-016**: In user review of sample outputs, at least 90% of reviewers can
  identify which criteria were executed and why the final index has its value.
- **SC-017**: In user review of sample outputs, 0 reviewed outputs describe the
  final index as a probability that the news is true or false.

## Assumptions

- The primary users are people evaluating shared news links, project reviewers,
  and maintainers auditing the analysis process.
- Version 1 scope includes only the fact-checking signal and writing-style
  signal for scoring.
- The reserved factual-claims criterion is visible in output for roadmap
  clarity but excluded from current score and coverage.
- The specified fact-checking source is treated as a source of published
  fact-check reviews, not as a universal reputation or truth oracle.
- The specified writing classifier is treated as a model for textual writing
  characteristics, not as proof of factual truth or falsity.
- Article text extraction must preserve semantic meaning; formatting cleanup is
  acceptable when it does not change article content.
- Missing metadata is acceptable when marked unavailable; fewer than 1,000
  extracted characters of main article text is not acceptable for current
  analysis.
- The system may return partial analysis when one current criterion fails and
  another current criterion remains available.
