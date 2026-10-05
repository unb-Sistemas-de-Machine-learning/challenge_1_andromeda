from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

from news_analysis.pipeline.errors import CriterionStatus
from news_analysis.pipeline.models import Article, SourceCredibilityCriterionResult, SourceCredibilitySignal


SIGNAL_WEIGHTS = {
    "https_final_url": 0.25,
    "canonical_url": 0.15,
    "publisher_metadata": 0.20,
    "author_metadata": 0.15,
    "publication_date": 0.15,
    "stable_domain": 0.10,
}


def evaluate_source_credibility(article: Article) -> SourceCredibilityCriterionResult:
    signals = [
        _signal(
            "https_final_url",
            "URL final usa HTTPS",
            _uses_https(article.final_url or article.original_url),
            "Conexão HTTPS no endereço final da notícia.",
        ),
        _signal(
            "canonical_url",
            "URL canônica declarada",
            bool(article.canonical_url),
            "Metadado canônico ajuda a identificar a página original.",
        ),
        _signal(
            "publisher_metadata",
            "Veículo identificado",
            bool(article.publisher),
            "Metadado de publicador extraído da página.",
        ),
        _signal(
            "author_metadata",
            "Autoria identificada",
            bool(article.author),
            "Metadado de autoria extraído da página.",
        ),
        _signal(
            "publication_date",
            "Data de publicação identificada",
            bool(article.published_at),
            "Metadado temporal extraído da página.",
        ),
        _signal(
            "stable_domain",
            "Domínio público estável",
            _has_stable_domain(article.final_url or article.original_url),
            "Domínio com nome e sufixo públicos no endereço final.",
        ),
    ]
    score = sum(signal.weight for signal in signals if signal.passed)
    return SourceCredibilityCriterionResult(
        available=True,
        status=CriterionStatus.EXECUTED,
        score=round(score, 4),
        signals=signals,
    )


def _signal(key: str, label: str, passed: bool, evidence: str) -> SourceCredibilitySignal:
    return SourceCredibilitySignal(
        key=key,
        label=label,
        passed=passed,
        weight=SIGNAL_WEIGHTS[key],
        evidence=evidence,
    )


def _uses_https(url: str | None) -> bool:
    return urlparse(url or "").scheme == "https"


def _has_stable_domain(url: str | None) -> bool:
    hostname = urlparse(url or "").hostname or ""
    try:
        ipaddress.ip_address(hostname)
        return False
    except ValueError:
        pass
    labels = [label for label in hostname.split(".") if label]
    return len(labels) >= 2 and all(label.replace("-", "").isalnum() for label in labels)
