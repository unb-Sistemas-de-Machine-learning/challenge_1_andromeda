from fastapi.testclient import TestClient

from news_analysis.api.app import app, rate_limiter
from news_analysis.api.dependencies import get_analyzer, get_repository
from news_analysis.article.extractor import ArticleExtractor
from news_analysis.pipeline.analyzer import NewsAnalyzer
from tests.conftest import FakeFactCheckClient, FakeFetcher


def test_analysis_can_be_retrieved_from_audit_store(temp_settings, repository, long_article_html, sample_fact_check_response):
    analyzer = NewsAnalyzer(
        temp_settings,
        repository,
        fetcher=FakeFetcher(long_article_html),
        fact_check_client=FakeFactCheckClient(sample_fact_check_response),
        extractor=ArticleExtractor(min_characters=1000),
    )
    app.dependency_overrides[get_analyzer] = lambda: analyzer
    app.dependency_overrides[get_repository] = lambda: repository
    rate_limiter.reset()
    client = TestClient(app)
    try:
        created = client.post("/analyses", json={"url": "https://93.184.216.34/article", "user_id": "audit-user"}).json()
        retrieved = client.get(f"/analyses/{created['id']}")
    finally:
        app.dependency_overrides.clear()
    assert retrieved.status_code == 200
    payload = retrieved.json()
    assert payload["id"] == created["id"]
    assert payload["pipeline_version"]["id"]
    assert "main_text" not in str(payload)
