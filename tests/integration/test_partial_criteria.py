from news_analysis.article.extractor import ArticleExtractor
from news_analysis.pipeline.analyzer import NewsAnalyzer
from tests.conftest import FakeFactCheckClient, FakeFetcher


def test_partial_availability_renormalizes_available_criterion(temp_settings, repository, long_article_html):
    analyzer = NewsAnalyzer(
        temp_settings,
        repository,
        fetcher=FakeFetcher(long_article_html),
        fact_check_client=FakeFactCheckClient({"claims": []}),
        extractor=ArticleExtractor(min_characters=1000),
    )
    analysis = analyzer.analyze("https://93.184.216.34/article")
    assert analysis.criteria.source_credibility.available is False
    assert analysis.criteria.writing_style.available is True
    assert analysis.final.coverage == 40
    assert analysis.final.effective_weights == {"writing_style": 1.0}
    assert analysis.final.score == analysis.criteria.writing_style.score * 100
