from news_analysis.article.extractor import ArticleExtractor
from news_analysis.pipeline.analyzer import NewsAnalyzer
from tests.conftest import FakeFactCheckClient, FakeFetcher


def test_repository_saves_and_retrieves_without_full_text(temp_settings, repository, long_article_html, sample_fact_check_response, long_article_text):
    analyzer = NewsAnalyzer(
        temp_settings,
        repository,
        fetcher=FakeFetcher(long_article_html),
        fact_check_client=FakeFactCheckClient(sample_fact_check_response),
        extractor=ArticleExtractor(min_characters=1000),
    )
    analysis = analyzer.analyze("https://93.184.216.34/article")
    stored = repository.get(analysis.id)
    serialized = str(stored)
    assert stored["pipeline_version"]["id"]
    assert stored["article"]["content_hash"]
    assert long_article_text not in serialized
    assert "main_text" not in serialized
