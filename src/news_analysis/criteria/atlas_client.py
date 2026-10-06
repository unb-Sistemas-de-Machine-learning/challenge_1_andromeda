"""Bounded Atlas REST client and the verified active-online/site adapter."""
from __future__ import annotations

import ipaddress
import json
import math
import time
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable
from urllib.parse import urljoin, urlsplit

import httpx

from news_analysis.article.safety import assert_url_is_safe
from news_analysis.criteria.credibility_config import AtlasConfig
from news_analysis.criteria.credibility_io import normalize_url, registrable_domain

ATLAS_BASE = 'https://api.atlas.jor.br/api/v1'
FIELDS = ('id', 'nome_veiculo', 'segmento', 'ativo', 'eh_jornal', 'data_fechamento')


class AtlasError(RuntimeError):
    """Safe error code: remote bodies, credentials and contacts are never logged."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def remaining(deadline: float) -> float:
    value = deadline - time.monotonic()
    if value <= 0:
        raise AtlasError('sync_budget_exceeded')
    return value


def site_domain(url: str, config: AtlasConfig) -> tuple[str, str]:
    """Accept a site identity, excluding multi-tenant/social/shortener domains."""
    normalized = normalize_url(url)
    host = (urlsplit(normalized).hostname or '').encode('idna').decode('ascii')
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError('invalid_site_url')
    if host == 'localhost' or host.endswith('.local'):
        raise ValueError('invalid_site_url')
    domain = registrable_domain(normalized)
    if any(host == item or host.endswith('.' + item) or domain == item for item in config.shared_domains + config.shortener_domains):
        raise ValueError('shared_or_shortener_domain')
    return domain, normalized


class AtlasClient:
    """Reuse an authenticated session during explicit synchronization, never analysis."""
    def __init__(self, config: AtlasConfig, client: httpx.Client | None = None,
                 resolver: Callable[[str, float], list[str]] | None = None):
        if config.base_url != ATLAS_BASE:
            raise ValueError('atlas_base_url_must_be_official')
        self.config = config
        self.client = client or httpx.Client(follow_redirects=False, headers={'User-Agent': 'Andromeda-Atlas/1.0'})
        self.owns_client = client is None
        self.resolver = resolver or self.resolve_site
        self.token: str | None = None
        self.token_expires = 0.0

    def close(self) -> None:
        if self.owns_client:
            self.client.close()

    def _authenticate(self, deadline: float) -> None:
        if self.config.auth_mode == 'dummy':
            body = self._json('GET', '/auth/dummy-jwt', deadline, auth=False)
        else:
            body = self._json('POST', '/auth/login', deadline, auth=False,
                              json_body={'email': self.config.email, 'password': self.config.password})
        if not isinstance(body, dict) or not isinstance(body.get('access_token'), str) or not body['access_token']:
            raise AtlasError('invalid_auth_response')
        try:
            lifetime = float(body['expires_in'])
        except (KeyError, TypeError, ValueError):
            raise AtlasError('invalid_auth_response') from None
        if not math.isfinite(lifetime) or lifetime <= 0:
            raise AtlasError('invalid_auth_response')
        self.token = body['access_token']
        self.token_expires = time.monotonic() + max(0, lifetime - min(30, lifetime / 10))

    def _json(self, method: str, path: str, deadline: float, *, auth: bool = True,
              params: list[tuple[str, str]] | None = None, json_body: dict | None = None) -> Any:
        if auth and (not self.token or self.token_expires <= time.monotonic()):
            self._authenticate(deadline)
        renewed, attempt = False, 0
        while True:
            wait = self.config.retry_delay * 2 ** attempt
            try:
                timeout = min(self.config.timeout, remaining(deadline))
                with self.client.stream(method, ATLAS_BASE + path, params=params, json=json_body,
                    headers={'Authorization': 'Bearer ' + self.token} if auth else {},
                    timeout=timeout, follow_redirects=False) as response:
                    code = response.status_code
                    if code == 401 and auth and not renewed:
                        renewed = True
                        self.token = None
                        self._authenticate(deadline)
                        continue
                    if code == 429 or code >= 500:
                        if attempt >= self.config.retries:
                            raise AtlasError(f'http_{code}')
                        retry_after = response.headers.get('Retry-After')
                        if retry_after:
                            try:
                                wait = max(0, float(retry_after))
                            except ValueError:
                                try:
                                    wait = max(0, (parsedate_to_datetime(retry_after) - datetime.now(timezone.utc)).total_seconds())
                                except (ValueError, TypeError):
                                    raise AtlasError('invalid_retry_after') from None
                    elif not 200 <= code < 300:
                        raise AtlasError(f'http_{code}')
                    else:
                        chunks, size = [], 0
                        for chunk in response.iter_bytes():
                            remaining(deadline)
                            size += len(chunk)
                            if size > self.config.max_bytes:
                                raise AtlasError('response_too_large')
                            chunks.append(chunk)
                        try:
                            return json.loads(b''.join(chunks))
                        except (ValueError, UnicodeError):
                            raise AtlasError('invalid_json') from None
            except httpx.HTTPError:
                if attempt >= self.config.retries:
                    raise AtlasError('transport_error') from None
            if not math.isfinite(wait) or wait >= remaining(deadline):
                raise AtlasError('sync_budget_exceeded')
            # Long throttles terminate this run instead of tying up the command.
            if wait > 30:
                raise AtlasError('retry_after_deferred')
            time.sleep(wait)
            attempt += 1

    def resolve_site(self, url: str, deadline: float) -> list[str]:
        """Follow official shortener redirects with a separate unauthenticated client.

        Only headers are read; do not download article bodies or forward Atlas JWT.
        """
        chain: list[str] = []
        with httpx.Client(headers={'User-Agent': 'Andromeda-Atlas/1.0'}, follow_redirects=False) as client:
            for hop in range(self.config.max_redirects + 1):
                url = normalize_url(url)
                assert_url_is_safe(url)
                chain.append(url)
                with client.stream('GET', url, timeout=min(self.config.timeout, remaining(deadline))) as response:
                    if response.is_redirect:
                        if hop == self.config.max_redirects or not response.headers.get('location'):
                            raise ValueError('site_redirect_limit')
                        url = urljoin(url, response.headers['location'])
                        continue
                    response.raise_for_status()
                    return chain
        raise ValueError('site_redirect_limit')

    def collect(self) -> dict[str, Any]:
        """Collect a complete JSON array and adapt only explicit Site channels.

        `eh_jornal` means newspaper according to /docs, so it is NOT used as a
        generic journalism classifier. Eligibility here is active Online listing.
        """
        deadline = time.monotonic() + self.config.sync_budget
        definitions = self._json('GET', '/data/analytic/definitions', deadline)
        if not isinstance(definitions, list) or not all(field in definitions for field in FIELDS):
            raise AtlasError('definitions_changed')
        params = [('ativo', '1'), ('segmento', 'Online')] + [('field[]', field) for field in FIELDS]
        rows = self._json('GET', '/data/analytic', deadline, params=params)
        if not isinstance(rows, list) or not rows:
            raise AtlasError('invalid_or_empty_collection')
        if len(rows) > self.config.max_records:
            raise AtlasError('too_many_records')
        exclusions: Counter[str] = Counter()
        links: dict[tuple, dict] = {}
        unresolved, shorteners = 0, 0
        for row in rows:
            remaining(deadline)
            if not isinstance(row, dict) or not all(field in row for field in FIELDS) or not isinstance(row.get('media_channels'), list):
                raise AtlasError('record_schema_changed')
            if type(row['id']) is not int or not isinstance(row['nome_veiculo'], str) or not row['nome_veiculo'].strip():
                raise AtlasError('record_schema_changed')
            if row['ativo'] not in (0, 1, '0', '1') or not isinstance(row['segmento'], str):
                raise AtlasError('record_schema_changed')
            if row['ativo'] not in (1, '1') or row['segmento'].lower() != 'online' or row['data_fechamento']:
                exclusions['ineligible'] += 1
                continue
            sites = []
            for channel in row['media_channels']:
                if not isinstance(channel, dict):
                    raise AtlasError('channel_schema_changed')
                definition = channel.get('channel')
                if not isinstance(definition, dict):
                    raise AtlasError('channel_schema_changed')
                if channel.get('channel_id') == 1 and definition.get('id') == 1 and definition.get('name') == 'Site' and not channel.get('deleted_at'):
                    if channel.get('media_id', row['id']) != row['id']:
                        raise AtlasError('channel_identity_conflict')
                    sites.append(channel.get('link'))
            accepted = False
            for url in sites:
                if not isinstance(url, str) or not url.strip():
                    exclusions['invalid_site_url'] += 1
                    continue
                try:
                    original = normalize_url(url.strip() if '://' in url else 'https://' + url.strip())
                    origin_domain = registrable_domain(original)
                    chain = [original]
                    if origin_domain in self.config.shortener_domains:
                        if shorteners >= self.config.max_shorteners:
                            exclusions['shortener_limit'] += 1
                            continue
                        shorteners += 1
                        chain = self.resolver(original, deadline)
                        if not chain or chain[0] != original:
                            raise ValueError('invalid_redirect_evidence')
                    final_domain, final_url = site_domain(chain[-1], self.config)
                    # Only the supplied site and its proven final destination are aliases.
                    candidates = [(final_domain, final_url)]
                    if len(chain) > 1:
                        try:
                            candidates.append(site_domain(original, self.config))
                        except ValueError:
                            pass
                        # Intermediate official destinations (e.g. bbcbrasil.com) are observable evidence.
                        for intermediate in chain[1:-1]:
                            try:
                                candidates.append(site_domain(intermediate, self.config))
                            except ValueError:
                                pass
                    for domain, _ in candidates:
                        link = dict(atlas_id=row['id'], name=row['nome_veiculo'], domain=domain,
                                    official_url=original, resolved_url=final_url,
                                    redirect_chain=chain if len(chain) > 1 else [], eligibility='active_online')
                        links[(domain, row['id'], original)] = link
                    accepted = True
                except AtlasError:
                    raise
                except Exception:
                    # A site-specific failure cannot invent a domain, or leak its URL/contacts.
                    exclusions['invalid_site_url'] += 1
            if not accepted:
                unresolved += 1
                exclusions['no_usable_site'] += 1
        if not links:
            raise AtlasError('no_usable_sites')
        eligible = len(rows) - exclusions['ineligible']
        return dict(links=list(links.values()), received_count=len(rows), accepted_count=eligible - unresolved,
                    excluded_count=exclusions['ineligible'] + unresolved, exclusion_reasons=dict(exclusions),
                    identity_complete=unresolved == 0, endpoint=ATLAS_BASE + '/data/analytic',
                    scope='active_online', mapping_version=self.config.mapping_version)
