import httpx
import pytest

from news_analysis.article.fetcher import ArticleFetcher
from news_analysis.pipeline.errors import AnalysisError, AnalysisStatus


def test_fetcher_enforces_download_cap(temp_settings):
    def handler(request):
        return httpx.Response(200, content=b"x" * (temp_settings.max_download_bytes + 1))

    fetcher = ArticleFetcher(temp_settings, httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(AnalysisError) as exc:
        fetcher.fetch("https://example.com/news")
    assert exc.value.status == AnalysisStatus.NEWS_FETCH_FAILED
    assert "5 MB" in exc.value.message


def test_fetcher_maps_timeout_to_fetch_failed(temp_settings):
    def handler(request):
        raise httpx.TimeoutException("boom")

    fetcher = ArticleFetcher(temp_settings, httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(AnalysisError) as exc:
        fetcher.fetch("https://example.com/news")
    assert exc.value.status == AnalysisStatus.NEWS_FETCH_FAILED
    assert exc.value.retryable is True
