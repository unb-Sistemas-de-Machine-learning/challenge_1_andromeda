import socket

import pytest

from news_analysis.article.safety import assert_url_is_safe
from news_analysis.pipeline.errors import AnalysisError, AnalysisStatus


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/news",
        "http://127.0.0.1/news",
        "http://10.0.0.5/news",
        "http://192.168.1.8/news",
        "http://169.254.10.1/news",
        "http://169.254.169.254/latest/meta-data",
    ],
)
def test_blocks_internal_and_metadata_addresses(url):
    with pytest.raises(AnalysisError) as exc:
        assert_url_is_safe(url)
    assert exc.value.status == AnalysisStatus.BLOCKED_INTERNAL_URL


def test_blocks_hostname_resolving_to_private_ip():
    def resolver(host, port, proto=socket.IPPROTO_TCP):
        return [(socket.AF_INET, socket.SOCK_STREAM, proto, "", ("10.0.0.1", 0))]

    with pytest.raises(AnalysisError) as exc:
        assert_url_is_safe("https://news.example/article", resolver=resolver)
    assert exc.value.status == AnalysisStatus.BLOCKED_INTERNAL_URL
