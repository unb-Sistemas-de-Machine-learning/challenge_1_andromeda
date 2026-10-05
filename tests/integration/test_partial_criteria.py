import pytest

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
    assert analysis.criteria.verifiable_facts.available is False
    assert analysis.criteria.writing_style.available is True
    assert analysis.criteria.source_credibility.available is True
    assert analysis.final.coverage == 50
    assert analysis.final.effective_weights == {"writing_style": 0.6, "source_credibility": 0.4}
    expected = (analysis.criteria.writing_style.score * 0.6 + analysis.criteria.source_credibility.score * 0.4) * 100
    assert analysis.final.score == pytest.approx(expected)


def test_model_load_failure_preserves_fact_check_flow(temp_settings, repository, long_article_html, sample_fact_check_response, monkeypatch):
    from news_analysis.criteria import writing_style
    def fail(cache):
        raise OSError("weights unavailable")
    monkeypatch.setattr(writing_style, "_load_model", fail)
    analyzer = NewsAnalyzer(
        temp_settings, repository,
        fetcher=FakeFetcher(long_article_html),
        fact_check_client=FakeFactCheckClient(sample_fact_check_response),
        extractor=ArticleExtractor(min_characters=1000),
    )
    analysis = analyzer.analyze("https://93.184.216.34/article")
    assert analysis.status == "SUCCESS"
    assert not analysis.criteria.writing_style.available
    assert analysis.criteria.writing_style.score is None
    assert analysis.criteria.source_credibility.available is True
    assert analysis.final.coverage == 70
    assert analysis.final.effective_weights == {
        "verifiable_facts": pytest.approx(0.7142857142857143),
        "source_credibility": pytest.approx(0.28571428571428575),
    }
    assert repository.get(analysis.id)["criteria"]["writing_style"]["error"]["code"] == "WRITING_MODEL_ERROR"
