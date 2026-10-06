"""Bounded network access and replaceable local source lists."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Any, Callable
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import httpx
import tldextract

from news_analysis.article.safety import assert_url_is_safe, validate_http_url
from news_analysis.criteria.credibility_config import CONFIG, CredibilityConfig

_extract = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)


def normalize_url(url: str, config: CredibilityConfig = CONFIG) -> str:
    """Remove fragments and known tracking keys, preserving semantic queries."""
    validate_http_url(url)
    parts = urlsplit(url)
    if parts.username or parts.password:
        raise ValueError('URLs com credenciais não são aceitas')
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith('utm_') and k.lower() not in config.tracking_parameters]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or '/', urlencode(query), ''))


def registrable_domain(url: str) -> str:
    """Use the bundled Public Suffix List without downloading during analysis."""
    host = (urlsplit(url).hostname or '').encode('idna').decode('ascii')
    domain = _extract(host).top_domain_under_public_suffix
    if not domain:
        raise ValueError('Domínio registrável não identificado')
    return domain.lower()


def load_domains(path: Path | None) -> set[str]:
    """Atlas integration point: replace this loader with a verified data source.

    JSON accepts a list of domain strings; CSV requires a `dominio` column.
    Missing configuration is unavailable, never an invented empty database.
    """
    return load_domain_base(path)[0]


def load_domain_base(path: Path | None) -> tuple[set[str], str]:
    """Parse and hash the same bytes so local recognition is reproducible."""
    if path is None:
        raise ValueError('Arquivo de domínios não configurado')
    raw = Path(path).read_bytes()
    with io.StringIO(raw.decode('utf-8-sig')) as stream:
        values = json.load(stream) if Path(path).suffix.lower() == '.json' else [row['dominio'] for row in csv.DictReader(stream)]
    if not isinstance(values, list) or not all(isinstance(x, str) and x.strip() for x in values):
        raise ValueError('Lista de domínios inválida')
    return {registrable_domain(x if '://' in x else 'https://' + x.strip()) for x in values}, hashlib.sha256(raw).hexdigest()


class TTLCache:
    """Small process-local bounded cache; failures are deliberately not cached."""
    def __init__(self, limit: int):
        self.limit = limit
        self.items: dict[str, tuple[float, Any]] = {}
        self.lock = Lock()

    def get(self, key: str, ttl: float, compute: Callable[[], Any]) -> Any:
        with self.lock:
            cached = self.items.get(key)
            if cached and cached[0] > monotonic():
                return cached[1]
        value = compute()
        with self.lock:
            if len(self.items) >= self.limit:
                self.items.pop(next(iter(self.items)))
            self.items[key] = (monotonic() + ttl, value)
        return value


class SourceNetwork:
    """Validate every redirect and leave TLS certificate verification enabled."""
    def __init__(self, config: CredibilityConfig = CONFIG):
        self.config = config

    def fetch(self, url: str) -> tuple[str, str]:
        with httpx.Client(timeout=self.config.timeout, headers={'User-Agent': self.config.user_agent}, follow_redirects=False) as client:
            for hop in range(self.config.max_redirects + 1):
                assert_url_is_safe(url)
                with client.stream('GET', url) as response:
                    if response.is_redirect:
                        if hop == self.config.max_redirects:
                            raise ValueError('Limite de redirecionamentos excedido')
                        url = urljoin(url, response.headers['location'])
                        continue
                    response.raise_for_status()
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > self.config.max_bytes:
                            raise ValueError('Resposta excede o limite de tamanho')
                        chunks.append(chunk)
                    return b''.join(chunks).decode(response.encoding or 'utf-8', errors='replace'), str(response.url)
        raise ValueError('Não foi possível resolver a URL')

    def creation_date(self, domain: str) -> datetime:
        """Query Registro.br first for .br; RDAP bootstrap for other suffixes."""
        endpoint = self.config.rdap_br if domain.endswith('.br') else self.config.rdap_other
        body, _ = self.fetch(endpoint + domain)
        dates = [datetime.fromisoformat(event['eventDate'].replace('Z', '+00:00'))
                 for event in json.loads(body).get('events', []) if event.get('eventAction') == 'registration']
        if not dates:
            raise ValueError('RDAP não informou a data de registro')
        return min(date.replace(tzinfo=date.tzinfo or timezone.utc) for date in dates)
