"""End-to-end local recognition, audit and API shape using explicit fixtures."""
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from news_analysis.atlas_sync import main, sync_atlas
from news_analysis.criteria.atlas_client import AtlasError
from news_analysis.criteria.credibility_config import AtlasConfig
from news_analysis.criteria.recognition import RecognitionProvider
from news_analysis.criteria.source_credibility import SourceCredibility
from news_analysis.pipeline.analyzer import NewsAnalyzer
from news_analysis.storage.atlas_repository import AtlasRepository
from tests.conftest import FakeFactCheckClient, FakeFetcher
from tests.unit.test_atlas_repository import collection


class AgeNetwork:
    def creation_date(self, domain):
        return datetime.now(timezone.utc) - timedelta(days=3000)


def test_atlas_evidence_and_blocklist_survive_new_snapshot(tmp_path, temp_settings, repository, long_article_html, sample_fact_check_response):
    atlas = AtlasRepository(temp_settings.db_path)
    with atlas.sync_lease(120) as owner:
        snapshot_id = atlas.publish(collection(), owner)
    settings = replace(temp_settings, atlas_enabled=True)
    config = settings.credibility_config()
    source = SourceCredibility(config, AgeNetwork(), RecognitionProvider(config, atlas))
    analyzer = NewsAnalyzer(settings, repository, fetcher=FakeFetcher(long_article_html, 'https://example.com/article'),
                            fact_check_client=FakeFactCheckClient(sample_fact_check_response), source_credibility=source)
    analysis = analyzer.analyze('https://93.184.216.34/article')
    assert analysis.criteria.credibility['criterios'][0]['pontos'] == 35
    assert analysis.criteria.credibility_evidence['evidence'][0]['snapshot_id'] == snapshot_id
    before = repository.get(analysis.id)
    with atlas.sync_lease(120) as owner:
        atlas.publish(collection('example.org'), owner)
    assert repository.get(analysis.id) == before
    assert source.recognition.lookup('example.com')['status'] == 'not_found'
    blocklist = tmp_path / 'blocked.json'
    blocklist.write_text('["example.com"]')
    source = SourceCredibility(replace(config, blocklist_path=blocklist), AgeNetwork(), RecognitionProvider(config, atlas))
    analyzer.source_credibility = source
    with atlas.sync_lease(120) as owner:
        atlas.publish(collection(), owner)
    blocked = analyzer.analyze('https://93.184.216.34/article')
    assert blocked.criteria.credibility['score_fonte'] == 0
    assert blocked.final.score == 35
    assert blocked.criteria.credibility_evidence['status'] == 'matched'
    blocked_before = repository.get(blocked.id)
    blocklist.write_text('[]')
    assert repository.get(blocked.id) == blocked_before
    assert blocked_before['criteria']['credibility_evidence']['blocklist']['matched_domains'] == ['example.com']
    assert blocked_before['criteria']['credibility_evidence']['veto']['reason_code'] == 'blocklist_match'


def test_dry_run_and_failure_keep_active(tmp_path):
    atlas = AtlasRepository(str(tmp_path / 'atlas.sqlite3'))
    config = AtlasConfig(enabled=True)
    class Client:
        def collect(self):
            return collection()
    result = sync_atlas(atlas, config, client=Client(), dry_run=True)
    assert result['status'] == 'validated'
    assert atlas.status()['active_snapshot_id'] is None
    published = sync_atlas(atlas, config, client=Client())
    class Failed:
        def collect(self):
            raise AtlasError('http_429')
    import pytest
    with pytest.raises(AtlasError):
        sync_atlas(atlas, config, client=Failed())
    assert atlas.status()['active_snapshot_id'] == published['snapshot_id']
    assert atlas.status()['last_error_code'] == 'http_429'


def test_cli_status_never_calls_remote(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('NEWS_ANALYSIS_DB_PATH', str(tmp_path / 'atlas.sqlite3'))
    monkeypatch.setenv('NEWS_ANALYSIS_ATLAS_ENABLED', 'true')
    monkeypatch.setattr('news_analysis.atlas_sync.AtlasClient', lambda *args: (_ for _ in ()).throw(AssertionError('remote call')))
    assert main(['status']) == 0
    assert json.loads(capsys.readouterr().out)['status'] == 'missing'
    monkeypatch.setenv('NEWS_ANALYSIS_ATLAS_ENABLED', 'invalid')
    assert main(['status']) == 2


def test_shared_api_service_reuses_cache_and_reads_new_snapshot(monkeypatch, temp_settings):
    from news_analysis.api import dependencies
    monkeypatch.setattr(dependencies, 'get_settings', lambda: replace(temp_settings, atlas_enabled=True))
    dependencies.get_atlas_repository.cache_clear()
    dependencies.get_source_credibility.cache_clear()
    try:
        first = dependencies.get_source_credibility()
        second = dependencies.get_source_credibility()
        assert first is second
        assert first.recognition.lookup('example.com')['status'] == 'unavailable'
        atlas = dependencies.get_atlas_repository()
        with atlas.sync_lease(120) as owner:
            snapshot_id = atlas.publish(collection(), owner)
        assert second.recognition.lookup('example.com')['evidence'][0]['snapshot_id'] == snapshot_id
    finally:
        dependencies.get_atlas_repository.cache_clear()
        dependencies.get_source_credibility.cache_clear()
