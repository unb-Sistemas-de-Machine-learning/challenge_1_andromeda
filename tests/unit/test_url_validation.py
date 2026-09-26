import pytest

from news_analysis.article.safety import validate_http_url
from news_analysis.pipeline.errors import AnalysisError, AnalysisStatus


def test_accepts_http_and_https_urls():
    assert validate_http_url("https://example.com/news").scheme == "https"
    assert validate_http_url("http://example.com/news").scheme == "http"


@pytest.mark.parametrize("url", ["not-a-url", "ftp://example.com/file", "https:///missing-host"])
def test_rejects_invalid_or_unsupported_urls(url):
    with pytest.raises(AnalysisError) as exc:
        validate_http_url(url)
    assert exc.value.status == AnalysisStatus.INVALID_URL
