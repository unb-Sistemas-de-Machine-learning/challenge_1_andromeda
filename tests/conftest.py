from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from news_analysis.config import Settings
from news_analysis.storage.audit_repository import AuditRepository


@pytest.fixture
def temp_settings():
    with tempfile.TemporaryDirectory() as directory:
        yield Settings(
            factcheck_api_key="test-key",
            db_path=str(Path(directory) / "audit.sqlite3"),
            fetch_timeout_seconds=0.1,
            max_download_bytes=1024,
            max_redirects=5,
            rate_limit_per_minute=10,
        )


@pytest.fixture
def repository(temp_settings):
    return AuditRepository(temp_settings.db_path)


@pytest.fixture
def long_article_text():
    return " ".join(["Texto principal confiavel sobre saude publica e dados oficiais."] * 40)


@pytest.fixture
def long_article_html(long_article_text):
    return f"<html><head><title>Vacina reduz casos graves</title></head><body><article><p>{long_article_text}</p></article></body></html>"


@pytest.fixture
def sample_fact_check_response():
    return {
        "claims": [
            {
                "text": "Vacina reduz casos graves",
                "languageCode": "pt",
                "claimReview": [
                    {
                        "publisher": {"name": "Agencia Checadora", "site": "checagem.example"},
                        "url": "https://checagem.example/vacina",
                        "title": "Vacina reduz casos graves e internações",
                        "reviewDate": "2026-01-01",
                        "textualRating": "Verdadeiro",
                    }
                ],
            }
        ]
    }


class FakeFactCheckClient:
    def __init__(self, response):
        self.response = response

    def search(self, query: str):
        return self.response


class FakeFetcher:
    def __init__(self, html: str, final_url: str = "https://news.example/article"):
        self.html = html
        self.final_url = final_url

    def fetch(self, url: str):
        return self.html, self.final_url
