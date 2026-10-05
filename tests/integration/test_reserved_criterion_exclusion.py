from news_analysis.article.extractor import ArticleExtractor
from news_analysis.pipeline.analyzer import NewsAnalyzer
from tests.conftest import FakeFactCheckClient, FakeFetcher


def test_source_credibility_affects_score_and_coverage(temp_settings, repository, long_article_html, sample_fact_check_response):
    analyzer = NewsAnalyzer(
        temp_settings,
        repository,
        fetcher=FakeFetcher(long_article_html),
        fact_check_client=FakeFactCheckClient(sample_fact_check_response),
        extractor=ArticleExtractor(min_characters=1000),
    )
    analysis = analyzer.analyze("https://93.184.216.34/article")
    assert analysis.criteria.source_credibility.available is True
    assert analysis.criteria.source_credibility.status == "EXECUTED"
    assert analysis.criteria.source_credibility.score is not None
    assert analysis.final.coverage == 100
    assert analysis.final.effective_weights == {
        "verifiable_facts": 0.5,
        "writing_style": 0.3,
        "source_credibility": 0.2,
    }
