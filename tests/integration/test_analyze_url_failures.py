from fastapi.testclient import TestClient

from news_analysis.api.app import app, rate_limiter
from news_analysis.api.dependencies import get_analyzer
from news_analysis.article.extractor import ArticleExtractor
from news_analysis.pipeline.analyzer import NewsAnalyzer
from tests.conftest import FakeFactCheckClient, FakeFetcher


def test_invalid_url_failure():
    rate_limiter.reset()
    response = TestClient(app).post("/analyses", json={"url": "not-a-url", "user_id": "invalid-user"})
    assert response.status_code == 400
    assert response.json()["status"] == "INVALID_URL"


def test_blocked_internal_url_failure():
    rate_limiter.reset()
    response = TestClient(app).post("/analyses", json={"url": "http://127.0.0.1/news", "user_id": "blocked-user"})
    assert response.status_code == 403
    assert response.json()["status"] == "BLOCKED_INTERNAL_URL"


def test_article_extraction_failure(temp_settings, repository):
    analyzer = NewsAnalyzer(
        temp_settings,
        repository,
        fetcher=FakeFetcher("<html><title>Curto</title><body>curto</body></html>", final_url="https://93.184.216.34/short"),
        fact_check_client=FakeFactCheckClient({"claims": []}),
        extractor=ArticleExtractor(min_characters=1000),
    )
    app.dependency_overrides[get_analyzer] = lambda: analyzer
    rate_limiter.reset()
    try:
        response = TestClient(app).post("/analyses", json={"url": "https://93.184.216.34/short", "user_id": "short-user"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 502
    assert response.json()["status"] == "ARTICLE_EXTRACTION_FAILED"
