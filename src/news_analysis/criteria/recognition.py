"""Combine a persistent Atlas index and explicitly configured local curation."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from news_analysis.criteria.credibility_config import CONFIG, CredibilityConfig
from news_analysis.criteria.credibility_io import load_domain_base
from news_analysis.storage.atlas_repository import AtlasRepository


class RecognitionProvider:
    """All lookups are local. Positive evidence wins; incomplete absence never does."""
    def __init__(self, config: CredibilityConfig = CONFIG, repository: AtlasRepository | None = None):
        self.config = config
        self.repository = repository

    def lookup(self, domain: str, *, now: datetime | None = None) -> dict[str, Any]:
        instant = now or datetime.now(timezone.utc)
        providers: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []
        ambiguous = False
        if self.config.atlas.enabled:
            provider: dict[str, Any] = dict(source='atlas', status='unavailable', reason_code='no_snapshot', complete=False)
            try:
                view = self.repository.lookup(domain) if self.repository else dict(snapshot=None, links=[])
                snapshot = view['snapshot']
                if snapshot:
                    age = (instant - datetime.fromisoformat(snapshot['created_at'])).total_seconds()
                    provider.update(snapshot_id=snapshot['id'], content_hash=snapshot['content_hash'],
                                    fetched_at=snapshot['created_at'], scope=snapshot['scope'],
                                    mapping_version=snapshot['mapping_version'], age_seconds=max(0, round(age)),
                                    complete=bool(snapshot['identity_complete']))
                    if age < 0 or age > self.config.atlas.max_age:
                        provider.update(freshness='expired', reason_code='expired_snapshot')
                    else:
                        provider.update(status='available', freshness='fresh' if age < self.config.atlas.refresh_after else 'stale',
                                        reason_code='ok' if snapshot['identity_complete'] else 'incomplete_identity_coverage')
                        # Conflict markers may be supplied by a future curated adapter.
                        ambiguous = domain in snapshot.get('ambiguous_domains', [])
                        if not ambiguous:
                            evidence.extend({'source': 'atlas', **link, 'snapshot_id': snapshot['id'],
                                             'content_hash': snapshot['content_hash'], 'fetched_at': snapshot['created_at'],
                                             'method': 'official_site_registrable_domain'} for link in view['links'])
                    if view.get('state', {}).get('last_error_code'):
                        provider['last_sync_error'] = view['state']['last_error_code']
            except Exception:
                provider.update(status='unavailable', reason_code='atlas_storage_unavailable')
            providers.append(provider)
        if self.config.recognized_path is not None:
            provider = dict(source='local', status='unavailable', reason_code='local_base_unavailable', complete=False)
            try:
                domains, digest = load_domain_base(self.config.recognized_path)
                provider.update(status='available', reason_code='ok', complete=True, content_hash=digest)
                if domain in domains:
                    evidence.append(dict(source='local', domain=domain, content_hash=digest, method='curated_domain_list'))
            except Exception:
                pass
            providers.append(provider)
        local_match = any(item['source'] == 'local' for item in evidence)
        if ambiguous and not local_match:
            status, reason = 'ambiguous', 'conflicting_identity'
        elif evidence:
            status, reason = 'matched', 'identified_in_base'
        elif not providers:
            status, reason = 'unavailable', 'no_sources_configured'
        elif all(item['status'] == 'available' and item['complete'] for item in providers):
            status, reason = 'not_found', 'not_found_in_consulted_bases'
        else:
            status, reason = 'unavailable', 'incomplete_or_unavailable_sources'
        return dict(status=status, domain=domain, checked_at=instant.isoformat(),
                    providers=providers, evidence=evidence, reason_code=reason)


def recognition_detail(result: dict[str, Any]) -> str:
    """Human-readable explanation without secrets or a fabricated reputation claim."""
    if result['status'] == 'matched':
        origins = sorted({item['source'] for item in result['evidence']})
        detail = 'Cadastro identificado no Atlas da Notícia' if 'atlas' in origins else 'Domínio presente na lista local curada'
        if origins == ['atlas', 'local']:
            detail += ' e na lista local curada'
        if any(item.get('freshness') == 'stale' for item in result['providers']):
            detail += '; usando cópia local dentro da validade, com atualização pendente'
        return detail + '; cadastro não comprova a veracidade da notícia'
    if result['status'] == 'not_found':
        return 'Não localizado nas bases consultadas; ausência não comprova desinformação'
    if result['status'] == 'ambiguous':
        return 'Vínculo do domínio com o cadastro é ambíguo; reconhecimento indisponível'
    if result['reason_code'] == 'no_sources_configured':
        return 'Nenhuma base de reconhecimento habilitada ou configurada'
    return 'Reconhecimento indisponível: base ausente, expirada, incompleta ou com falha'
