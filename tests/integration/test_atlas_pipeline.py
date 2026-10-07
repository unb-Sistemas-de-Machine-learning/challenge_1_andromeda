"""End-to-end local recognition, audit and API shape using explicit fixtures."""
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from news_analysis.atlas_sync import atlas_status, main, refresh_atlas_for_analysis, sync_atlas
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
        dependencies.get_analyzer.cache_clear()
        assert dependencies.get_analyzer().auto_refresh_atlas is True
        assert first.recognition.lookup('example.com')['status'] == 'unavailable'
        atlas = dependencies.get_atlas_repository()
        with atlas.sync_lease(120) as owner:
            snapshot_id = atlas.publish(collection(), owner)
        assert second.recognition.lookup('example.com')['evidence'][0]['snapshot_id'] == snapshot_id
    finally:
        dependencies.get_atlas_repository.cache_clear()
        dependencies.get_source_credibility.cache_clear()
        dependencies.get_analyzer.cache_clear()


def test_refresh_runs_once_per_day(tmp_path):
    atlas = AtlasRepository(str(tmp_path / 'atlas.sqlite3'))
    config = AtlasConfig(enabled=True)
    class Client:
        calls = 0
        def collect(self):
            self.calls += 1
            return collection()
    client = Client()
    assert refresh_atlas_for_analysis(atlas, config, client=client) == 'published'
    assert refresh_atlas_for_analysis(atlas, config, client=client) == 'current'
    assert client.calls == 1


def test_refresh_uses_sao_paulo_day_across_utc_midnight():
    class Repository:
        def status(self):
            return {'active_snapshot_id': 'snapshot',
                    'last_success_at': datetime(2026, 10, 7, 0, 30, tzinfo=timezone.utc).timestamp()}
    class Client:
        def collect(self):
            raise AssertionError('The snapshot was updated today in São Paulo')
    assert refresh_atlas_for_analysis(Repository(), AtlasConfig(enabled=True),
                                      now=datetime(2026, 10, 7, 1, 30, tzinfo=timezone.utc), client=Client()) == 'current'


def test_status_marks_yesterday_snapshot_as_pending():
    class Repository:
        def status(self):
            return {'active_snapshot_id': 'snapshot', 'last_success_at': None, 'last_attempt_at': None,
                    'last_error_code': None, 'snapshot': {
                        'created_at': (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                    }}
    assert atlas_status(Repository(), AtlasConfig(enabled=True))['status'] == 'stale'


def test_failed_daily_refresh_keeps_previous_snapshot(tmp_path):
    atlas = AtlasRepository(str(tmp_path / 'atlas.sqlite3'))
    with atlas.sync_lease(120) as owner:
        snapshot_id = atlas.publish(collection(), owner)
    class Failed:
        def collect(self):
            raise AtlasError('transport_error')
    later = datetime.now(timezone.utc) + timedelta(days=1)
    assert refresh_atlas_for_analysis(atlas, AtlasConfig(enabled=True), now=later, client=Failed()) == 'unavailable'
    assert atlas.status()['active_snapshot_id'] == snapshot_id
    assert atlas.status()['last_error_code'] == 'transport_error'


def test_analysis_refreshes_atlas_before_source_lookup(monkeypatch, temp_settings, repository,
                                                       long_article_html, sample_fact_check_response):
    atlas = AtlasRepository(temp_settings.db_path)
    settings = replace(temp_settings, atlas_enabled=True)
    config = settings.credibility_config()
    source = SourceCredibility(config, AgeNetwork(), RecognitionProvider(config, atlas))
    calls = []
    def refresh(repo, atlas_config):
        calls.append(atlas_config.enabled)
        with repo.sync_lease(120) as owner:
            repo.publish(collection(), owner)
        return 'published'
    monkeypatch.setattr('news_analysis.pipeline.analyzer.refresh_atlas_for_analysis', refresh)
    analyzer = NewsAnalyzer(settings, repository,
                            fetcher=FakeFetcher(long_article_html, 'https://example.com/article'),
                            fact_check_client=FakeFactCheckClient(sample_fact_check_response),
                            source_credibility=source, auto_refresh_atlas=True, atlas_repository=atlas)
    analysis = analyzer.analyze('https://93.184.216.34/article')
    assert calls == [True]
    assert analysis.criteria.credibility['criterios'][0]['pontos'] == 35
