from fastapi.testclient import TestClient

from news_analysis.api.app import app, rate_limiter
from news_analysis.api.dependencies import get_analyzer, get_repository
from news_analysis.article.extractor import ArticleExtractor
from news_analysis.pipeline.analyzer import NewsAnalyzer
from tests.conftest import FakeFactCheckClient, FakeFetcher


def test_successful_post_analysis_with_mocked_services(temp_settings, repository, long_article_html, sample_fact_check_response):
    analyzer = NewsAnalyzer(
        temp_settings,
        repository,
        fetcher=FakeFetcher(long_article_html, final_url="https://93.184.216.34/article"),
        fact_check_client=FakeFactCheckClient(sample_fact_check_response),
        extractor=ArticleExtractor(min_characters=1000),
    )
    app.dependency_overrides[get_analyzer] = lambda: analyzer
    app.dependency_overrides[get_repository] = lambda: repository
    rate_limiter.reset()
    try:
        response = TestClient(app).post(
            "/analyses",
            json={"url": "https://93.184.216.34/article", "user_id": "success-user"},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "SUCCESS"
    assert payload["article"]["extracted_character_count"] >= 1000
    assert payload["criteria"]["source_credibility"]["available"] is True
    assert payload["criteria"]["writing_style"]["available"] is True
    assert payload["final"]["coverage"] == 100
    assert "probability" in payload["final"]["limitation"]
    assert "main_text" not in str(payload)
