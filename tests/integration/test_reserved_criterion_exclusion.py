from news_analysis.article.extractor import ArticleExtractor
from news_analysis.pipeline.analyzer import NewsAnalyzer
from tests.conftest import FakeFactCheckClient, FakeFetcher


def test_reserved_factual_claims_does_not_affect_score_or_coverage(temp_settings, repository, long_article_html, sample_fact_check_response):
    analyzer = NewsAnalyzer(
        temp_settings,
        repository,
        fetcher=FakeFetcher(long_article_html),
        fact_check_client=FakeFactCheckClient(sample_fact_check_response),
        extractor=ArticleExtractor(min_characters=1000),
    )
    analysis = analyzer.analyze("https://93.184.216.34/article")
    assert analysis.criteria.factual_claims.available is False
    assert analysis.criteria.factual_claims.status == "NOT_IMPLEMENTED"
    assert analysis.criteria.factual_claims.score is None
    assert analysis.final.coverage == 100
    assert "factual_claims" not in analysis.final.effective_weights
