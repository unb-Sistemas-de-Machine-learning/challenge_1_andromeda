from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from news_analysis.article.extractor import ArticleExtractor
from news_analysis.article.fetcher import ArticleFetcher
from news_analysis.article.safety import assert_url_is_safe, validate_http_url
from news_analysis.config import Settings
from news_analysis.criteria.fact_check import (
    FactCheckClient,
    build_fact_check_queries,
    error_fact_check,
    evaluate_fact_checks,
)
from news_analysis.criteria.writing_style import WritingStyleClassifier
from news_analysis.criteria.source_credibility import SourceCredibility
from news_analysis.criteria.credibility_policy import SOURCE_SCORE_CAP
from news_analysis.pipeline.aggregation import aggregate_final_score, contribution
from news_analysis.pipeline.errors import AnalysisError, AnalysisStatus
from news_analysis.pipeline.models import (
    Analysis,
    CriteriaSet,
    ErrorInfo,
    FactCheckCriterionResult,
    FinalScore,
    WritingStyleCriterionResult,
)
from news_analysis.pipeline.version import current_pipeline_version
from news_analysis.storage.audit_repository import AuditRepository

LIMITATIONS = [
    "The final index is an operational combination of executed criteria, not a probability that the news is true or false.",
    "Writing-style predictions are model signals and not factual verdicts.",
    "Unavailable evidence is reported and excluded from scoring rather than treated as negative evidence.",
]


class NewsAnalyzer:
    def __init__(
        self,
        settings: Settings,
        repository: AuditRepository,
        fetcher: ArticleFetcher | None = None,
        extractor: ArticleExtractor | None = None,
        fact_check_client: FactCheckClient | None = None,
        writing_classifier: WritingStyleClassifier | None = None,
        source_credibility: SourceCredibility | None = None,
    ):
        self.settings = settings
        self.repository = repository
        self.fetcher = fetcher or ArticleFetcher(settings)
        self.extractor = extractor or ArticleExtractor(settings.min_extracted_characters)
        self.fact_check_client = fact_check_client or FactCheckClient(settings)
        self.writing_classifier = writing_classifier or WritingStyleClassifier(cache_dir=settings.model_cache)
        if source_credibility is None:
            from news_analysis.criteria.recognition import RecognitionProvider
            from news_analysis.storage.atlas_repository import AtlasRepository
            config = settings.credibility_config()
            source_credibility = SourceCredibility(config, recognition=RecognitionProvider(
                config, AtlasRepository(settings.db_path) if config.atlas.enabled else None))
        self.source_credibility = source_credibility

    def analyze(self, url: str, claim: str | None = None) -> Analysis:
        analysis_id = str(uuid4())
        created_at = datetime.now(timezone.utc)
        try:
            validate_http_url(url)
            assert_url_is_safe(url)
            html, final_url = self.fetcher.fetch(url)
            extracted = self.extractor.extract(html, original_url=url, final_url=final_url)
        except AnalysisError as exc:
            analysis = self._terminal_analysis(analysis_id, url, created_at, exc)
            if claim and claim.strip():
                analysis.input["claim"] = claim.strip()
            self.repository.save(analysis)
            return analysis

        fact_check = self._run_fact_check(extracted.article.title, extracted.main_text, claim)
        writing = self.writing_classifier.classify(extracted.main_text)
        final = aggregate_final_score(fact_check.score, writing.score)
        self._attach_contributions(fact_check, writing, final)
        credibility, credibility_evidence = self.source_credibility.calculate_with_evidence(url, page=(html, final_url))
        final.score_before_veto = final.score
        final.source_veto_applied = False
        if credibility['veto_dominio_suspeito'] and final.score is not None:
            final.score = min(final.score, SOURCE_SCORE_CAP)
            final.source_veto_applied = True
            final.formula = f"min({SOURCE_SCORE_CAP}, {final.formula}); veto da fonte"

        criteria = CriteriaSet(
            verifiable_facts=fact_check,
            writing_style=writing,
            credibility=credibility,
            credibility_evidence=credibility_evidence,
        )
        analysis = Analysis(
            id=analysis_id,
            status=AnalysisStatus.SUCCESS,
            input={"url": url, **({"claim": claim.strip()} if claim and claim.strip() else {})},
            article=extracted.article,
            criteria=criteria,
            final=final,
            pipeline_version=current_pipeline_version(self.source_credibility.config),
            limitations=self._limitations_for(final.coverage),
            created_at=created_at,
            completed_at=datetime.now(timezone.utc),
        )
        self.repository.save(analysis)
        return analysis

    def _run_fact_check(self, title: str | None, text: str, claim: str | None = None) -> FactCheckCriterionResult:
        explicit_claim = claim.strip() if claim and claim.strip() else None
        target_claim = explicit_claim or title
        claim_origin = "user" if explicit_claim else "article_title_or_excerpt"
        queries = build_fact_check_queries(target_claim, explicit_claim or text)
        search_attempts: list[dict[str, object]] = []
        best_result: FactCheckCriterionResult | None = None
        try:
            for query in queries:
                raw = self.fact_check_client.search(query)
                claims_count = len(raw.get("claims", []))
                search_attempts.append({"query": query, "claims_count": claims_count})
                raw = {**raw, "search_attempts": search_attempts}
                result = evaluate_fact_checks(raw, title, text, query, target_claim=explicit_claim, claim_origin=claim_origin)
                if result.available:
                    return result
                if raw.get("unavailable_reason") == "missing_api_key":
                    return result
                if best_result is None or _is_better_fact_check_result(result, best_result):
                    best_result = result
            if best_result is not None:
                if best_result.error:
                    best_result.error.details = {
                        **(best_result.error.details or {}),
                        "attempted_queries": [attempt["query"] for attempt in search_attempts],
                    }
                return best_result
            return evaluate_fact_checks({"claims": [], "search_attempts": search_attempts}, title, text, "", target_claim=explicit_claim, claim_origin=claim_origin)
        except Exception as exc:
            result = error_fact_check(queries[0] if queries else "", exc)
            result.target_claim = explicit_claim or title or text[:240]
            result.claim_origin = claim_origin
            result.search_attempts = search_attempts
            return result

    def _terminal_analysis(self, analysis_id: str, url: str, created_at: datetime, exc: AnalysisError) -> Analysis:
        final = aggregate_final_score(None, None)
        criteria = CriteriaSet(
            verifiable_facts=FactCheckCriterionResult(
                available=False,
                status="UNAVAILABLE",
                score=None,
                query="",
                reviews_count=0,
                applicable_reviews_count=0,
                reviews=[],
                error=ErrorInfo(code="CRITERION_UNAVAILABLE", message="Analysis did not reach fact-checking.", retryable=False),
            ),
            writing_style=WritingStyleCriterionResult(
                available=False,
                status="UNAVAILABLE",
                score=None,
                model="vzani/portuguese-fake-news-classifier-bertimbau-combined",
                model_version=current_pipeline_version().writing_model_revision,
                segments_analyzed=0,
                segments=[],
                qualitative_state=None,
                limitation="Writing-style labels are model signals, not factual verdicts about the news.",
                error=ErrorInfo(code="CRITERION_UNAVAILABLE", message="Analysis did not reach writing-style classification.", retryable=False),
            ),
        )
        return Analysis(
            id=analysis_id,
            status=exc.status,
            input={"url": url},
            criteria=criteria,
            final=final,
            pipeline_version=current_pipeline_version(self.source_credibility.config),
            limitations=LIMITATIONS,
            error=ErrorInfo(code=exc.status.value, message=exc.message, retryable=exc.retryable, details=exc.details or None),
            created_at=created_at,
            completed_at=datetime.now(timezone.utc),
        )

    def _attach_contributions(
        self,
        fact_check: FactCheckCriterionResult,
        writing: WritingStyleCriterionResult,
        final: FinalScore,
    ) -> None:
        fact_check.effective_weight = final.effective_weights.get("verifiable_facts")
        writing.effective_weight = final.effective_weights.get("writing_style")
        fact_check.contribution = contribution(fact_check.score, fact_check.effective_weight)
        writing.contribution = contribution(writing.score, writing.effective_weight)

    def _limitations_for(self, coverage: float) -> list[str]:
        coverage_message = {
            100: "Both current criteria were executed.",
            60: "Only the fact-checking criterion contributed to the final index.",
            40: "Only the writing-style criterion contributed to the final index.",
            0: "No current criteria contributed to the final index.",
        }.get(coverage, "Criterion coverage was calculated from available current criteria.")
        return [*LIMITATIONS, coverage_message]


def _is_better_fact_check_result(candidate: FactCheckCriterionResult, current: FactCheckCriterionResult) -> bool:
    if candidate.applicable_reviews_count != current.applicable_reviews_count:
        return candidate.applicable_reviews_count > current.applicable_reviews_count
    return candidate.reviews_count > current.reviews_count
