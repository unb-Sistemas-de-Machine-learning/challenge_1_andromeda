from datetime import datetime, timedelta, timezone

import pytest

from news_analysis.storage.atlas_repository import AtlasRepository, SyncBusy


def collection(domain='example.com', complete=True, count=1):
    return dict(links=[dict(atlas_id=1, name='Veículo simulado', domain=domain, official_url='https://' + domain,
        resolved_url='https://' + domain, redirect_chain=[], eligibility='active_online')], received_count=count,
        accepted_count=1, excluded_count=0, exclusion_reasons={}, identity_complete=complete,
        endpoint='https://api.atlas.jor.br/api/v1/data/analytic', scope='active_online', mapping_version='atlas-site-v1')


def test_snapshot_survives_restart_and_old_version_is_retained(tmp_path):
    repo = AtlasRepository(str(tmp_path / 'atlas.sqlite3'))
    with repo.sync_lease(120) as owner:
        old = repo.publish(collection(), owner)
    with repo.sync_lease(120) as owner:
        new = repo.publish(collection('example.org'), owner)
    restarted = AtlasRepository(repo.db_path)
    assert restarted.lookup('example.com')['links'] == []
    assert restarted.lookup('example.org')['snapshot']['id'] == new
    assert restarted.snapshot(old)['id'] == old


def test_failed_publication_keeps_active_and_records_error(tmp_path):
    repo = AtlasRepository(str(tmp_path / 'atlas.sqlite3'))
    with repo.sync_lease(120) as owner:
        old = repo.publish(collection(count=10), owner)
    with pytest.raises(ValueError):
        with repo.sync_lease(120) as owner:
            repo.publish(collection(count=1), owner)
    assert repo.status()['active_snapshot_id'] == old
    assert repo.status()['last_error_code']


def test_lease_prevents_concurrency_and_recovers(tmp_path):
    repo = AtlasRepository(str(tmp_path / 'atlas.sqlite3'))
    now = datetime.now(timezone.utc)
    with repo.sync_lease(120, now=now):
        with pytest.raises(SyncBusy):
            with AtlasRepository(repo.db_path).sync_lease(120, now=now):
                pass
        with repo.sync_lease(120, now=now + timedelta(seconds=121)) as newer:
            repo.publish(collection(), newer)
    assert repo.lookup('example.com')['links']
