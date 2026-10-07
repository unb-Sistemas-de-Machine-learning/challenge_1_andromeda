from datetime import datetime, timedelta, timezone

import pytest

from news_analysis.criteria.credibility_config import CredibilityConfig
from news_analysis.criteria.source_credibility import SourceCredibility
from news_analysis.pipeline.analyzer import NewsAnalyzer
from tests.conftest import FakeFactCheckClient, FakeFetcher


def test_source_veto_persisted_without_overwriting_fact_check(tmp_path, temp_settings, repository, long_article_html, sample_fact_check_response):
    path = tmp_path / 'empty.json'
    path.write_text('[]')

    class Network:
        def creation_date(self, domain):
            return datetime.now(timezone.utc) - timedelta(days=10)

    source = SourceCredibility(CredibilityConfig(recognized_path=path, blocklist_path=path), Network())
    analyzer = NewsAnalyzer(temp_settings, repository,
                            fetcher=FakeFetcher(long_article_html, 'https://example.com/article'),
                            fact_check_client=FakeFactCheckClient(sample_fact_check_response),
                            source_credibility=source)
    analysis = analyzer.analyze('https://93.184.216.34/article')
    assert analysis.criteria.credibility['score_fonte'] == 5
    assert analysis.criteria.credibility['intended_weight'] == 0.20
    assert analysis.criteria.credibility['effective_weight'] == 0.20
    assert analysis.criteria.credibility['contribution'] == 1.0
    assert analysis.final.score_before_veto == round(
        0.65 * analysis.criteria.verifiable_facts.score * 100
        + 0.20 * analysis.criteria.credibility['score_fonte']
        + 0.15 * analysis.criteria.writing_style.score * 100, 4,
    )
    assert analysis.final.score == 35
    assert 'min(35' in analysis.final.formula
    stored = repository.get(analysis.id)
    assert stored['criteria']['credibility'] == analysis.criteria.credibility
    assert stored['criteria']['verifiable_facts']['available']
    assert analysis.final.score_before_veto > 35
    assert analysis.final.source_veto_applied is True
    assert stored['criteria']['credibility_evidence']['veto']['reason_code'] == 'score_below_threshold'
    assert stored['pipeline_version']['credibility_policy_hash'] == stored['criteria']['credibility_evidence']['policy_hash']


def test_unavailable_source_does_not_cap_pipeline_score(temp_settings, repository, long_article_html, sample_fact_check_response):
    class Unavailable(SourceCredibility):
        def calculate_with_evidence(self, url, *, page=None):
            # Exercise the real unavailable-source path, independently of reused HTML.
            return super().calculate_with_evidence(url)

    class FailedNetwork:
        def fetch(self, url):
            raise TimeoutError('simulated outage')

    source = Unavailable(network=FailedNetwork())
    analyzer = NewsAnalyzer(temp_settings, repository, fetcher=FakeFetcher(long_article_html),
                            fact_check_client=FakeFactCheckClient(sample_fact_check_response), source_credibility=source)
    analysis = analyzer.analyze('https://93.184.216.34/article')
    assert analysis.criteria.credibility['score_fonte'] is None
    assert analysis.criteria.credibility['status'] == 'UNAVAILABLE'
    assert analysis.criteria.credibility['effective_weight'] is None
    assert analysis.final.coverage == 80
    assert analysis.final.effective_weights == pytest.approx({'verifiable_facts': 0.8125, 'writing_style': 0.1875})
    assert analysis.final.score > 35
    assert analysis.final.score == analysis.final.score_before_veto
    assert analysis.final.source_veto_applied is False
    assert analysis.criteria.credibility_evidence['veto']['reason_code'] == 'source_unavailable'
    assert repository.get(analysis.id)['criteria']['credibility']['score_fonte'] is None
