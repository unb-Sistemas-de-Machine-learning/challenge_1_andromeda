from dataclasses import replace
from datetime import datetime, timedelta, timezone

from news_analysis.criteria.credibility_config import CredibilityConfig, AtlasConfig
from news_analysis.criteria.recognition import RecognitionProvider
from news_analysis.storage.atlas_repository import AtlasRepository


def publish(repo, now, complete=True):
    from tests.unit.test_atlas_repository import collection
    with repo.sync_lease(120, now=now) as owner:
        return repo.publish(collection(complete=complete), owner, now=now)


def test_available_partial_expired_and_local_fallback(tmp_path):
    now = datetime.now(timezone.utc)
    repo = AtlasRepository(str(tmp_path / 'atlas.sqlite3'))
    config = CredibilityConfig(atlas=AtlasConfig(enabled=True))
    provider = RecognitionProvider(config, repo)
    assert provider.lookup('example.com', now=now)['status'] == 'unavailable'
    first = publish(repo, now, complete=False)
    match = provider.lookup('example.com', now=now)
    assert match['status'] == 'matched'
    assert match['providers'][0]['snapshot_id'] == first
    assert provider.lookup('missing.com', now=now)['status'] == 'unavailable'
    assert provider.lookup('example.com', now=now + timedelta(days=2))['providers'][0]['freshness'] == 'stale'
    assert provider.lookup('example.com', now=now + timedelta(days=8))['status'] == 'unavailable'
    local = tmp_path / 'local.json'
    local.write_text('["example.com"]')
    fallback = RecognitionProvider(replace(config, recognized_path=local), repo)
    assert fallback.lookup('example.com', now=now + timedelta(days=8))['status'] == 'matched'


def test_complete_absence_and_corrupt_local_preserve_missingness(tmp_path):
    now = datetime.now(timezone.utc)
    repo = AtlasRepository(str(tmp_path / 'atlas.sqlite3'))
    publish(repo, now)
    config = CredibilityConfig(atlas=AtlasConfig(enabled=True))
    assert RecognitionProvider(config, repo).lookup('other.com', now=now)['status'] == 'not_found'
    broken = replace(config, recognized_path=tmp_path / 'missing.json')
    assert RecognitionProvider(broken, repo).lookup('other.com', now=now)['status'] == 'unavailable'


def test_snapshot_update_is_visible_without_recreating_provider(tmp_path):
    now = datetime.now(timezone.utc)
    repo = AtlasRepository(str(tmp_path / 'atlas.sqlite3'))
    provider = RecognitionProvider(CredibilityConfig(atlas=AtlasConfig(enabled=True)), repo)
    first = publish(repo, now)
    second = publish(repo, now + timedelta(seconds=1))
    assert first != second
    assert provider.lookup('example.com', now=now + timedelta(seconds=2))['providers'][0]['snapshot_id'] == second
