from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from news_analysis.config import Settings
from news_analysis.storage.audit_repository import AuditRepository


class FakeWritingTokenizer:
    model_input_names = ["input_ids", "attention_mask"]

    def __call__(self, text, *, max_length, **kwargs):
        size = max_length - 2
        ids, masks, offsets = [], [], []
        for start in range(0, len(text), size):
            end = min(start + size, len(text))
            window = [101, *[ord(char) for char in text[start:end]], 102]
            ids.append(window)
            masks.append([1] * len(window))
            offsets.append([(0, 0), *[(i, i + 1) for i in range(start, end)], (0, 0)])
        return {"input_ids": ids, "attention_mask": masks, "offset_mapping": offsets}


class FakeWritingModel:
    def __init__(self, true_probability=0.8):
        from types import SimpleNamespace
        self.config = SimpleNamespace(num_labels=2, max_position_embeddings=512)
        self.true_probability = true_probability
        self.inputs = []

    def __call__(self, **inputs):
        from types import SimpleNamespace
        import torch
        self.inputs.append(inputs)
        logits = torch.tensor([[1 - self.true_probability, self.true_probability]]).log()
        return SimpleNamespace(logits=logits)


@pytest.fixture(autouse=True)
def mocked_source_service(monkeypatch):
    """Existing pipeline tests isolate source networking; source tests inject it."""
    from types import SimpleNamespace
    monkeypatch.setattr('news_analysis.pipeline.analyzer.SourceCredibility', lambda config, **kwargs: SimpleNamespace(
        config=config,
        calculate_with_evidence=lambda *args, **kwargs: (dict(url_original=args[0], url_final=args[0], dominio='example.com',
            score_fonte=50, confianca_fonte='alta', criterios=[], flags=[], veto_dominio_suspeito=False, erros=[]), None)))


@pytest.fixture(autouse=True)
def mocked_writing_model(monkeypatch):
    """Keep normal tests deterministic and independent of downloads/real weights."""
    from news_analysis.criteria import writing_style
    model = FakeWritingModel()
    monkeypatch.setattr(writing_style, "_load_model", lambda cache_dir: (FakeWritingTokenizer(), model))
    return model


@pytest.fixture
def temp_settings():
    with tempfile.TemporaryDirectory() as directory:
        yield Settings(
            factcheck_api_key="test-key",
            writing_onnx_path=None,
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
