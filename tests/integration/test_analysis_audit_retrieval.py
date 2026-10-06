from fastapi.testclient import TestClient

from news_analysis.api.app import app, rate_limiter
from news_analysis.api.dependencies import get_analyzer, get_repository
from news_analysis.article.extractor import ArticleExtractor
from news_analysis.pipeline.analyzer import NewsAnalyzer
from tests.conftest import FakeFactCheckClient, FakeFetcher
import json
from contextlib import closing
import pytest


def test_analysis_can_be_retrieved_from_audit_store(temp_settings, repository, long_article_html, sample_fact_check_response):
    analyzer = NewsAnalyzer(
        temp_settings,
        repository,
        fetcher=FakeFetcher(long_article_html),
        fact_check_client=FakeFactCheckClient(sample_fact_check_response),
        extractor=ArticleExtractor(min_characters=1000),
    )
    app.dependency_overrides[get_analyzer] = lambda: analyzer
    app.dependency_overrides[get_repository] = lambda: repository
    rate_limiter.reset()
    client = TestClient(app)
    try:
        created = client.post("/analyses", json={"url": "https://93.184.216.34/article", "user_id": "audit-user"}).json()
        retrieved = client.get(f"/analyses/{created['id']}")
    finally:
        app.dependency_overrides.clear()
    assert retrieved.status_code == 200
    payload = retrieved.json()
    assert payload["id"] == created["id"]
    assert payload["pipeline_version"]["id"]
    assert "main_text" not in str(payload)


@pytest.mark.parametrize('fact_available', [True, False])
def test_v4_history_preserves_independent_source_facts_weights_and_storage(
        fact_available, temp_settings, repository, long_article_html, sample_fact_check_response):
    analyzer = NewsAnalyzer(temp_settings, repository, fetcher=FakeFetcher(long_article_html),
                            fact_check_client=FakeFactCheckClient(sample_fact_check_response))
    analysis = analyzer.analyze('https://93.184.216.34/article')
    payload = repository.get(analysis.id)
    payload['criteria'].pop('credibility', None)
    payload['criteria'].pop('credibility_evidence', None)
    payload['criteria']['verifiable_facts']['intended_weight'] = .5
    payload['criteria']['verifiable_facts']['available'] = fact_available
    payload['criteria']['verifiable_facts']['score'] = 1 if fact_available else None
    payload['criteria']['writing_style']['intended_weight'] = .3
    source = dict(available=True, status='EXECUTED', score=1,
                  method='metadata_transparency_signals', intended_weight=.2,
                  effective_weight=.2 if fact_available else .4, contribution=20 if fact_available else 40,
                  signals=[dict(key='https_final_url', label='HTTPS', passed=True, weight=.25, evidence='HTTPS')])
    payload['criteria']['source_credibility'] = source
    payload['final'] = dict(score=94 if fact_available else 88, coverage=100 if fact_available else 50,
        intended_weights=dict(verifiable_facts=.5, writing_style=.3, source_credibility=.2),
        effective_weights=dict(verifiable_facts=.5, writing_style=.3, source_credibility=.2) if fact_available else
                          dict(writing_style=.6, source_credibility=.4),
        formula='historical v4 formula', limitation='historical v4 limitation')
    payload['pipeline_version'] = dict(id='historical-v4', rules_version='analysis-rules-v4-source-credibility',
        fact_check_mapping_version='v2', writing_model_name='historical-model', dependency_versions={})
    raw = json.dumps(payload)
    with closing(repository._connect()) as connection:
        connection.execute('UPDATE analyses SET payload_json=? WHERE id=?', (raw, analysis.id))
        connection.commit()
    app.dependency_overrides[get_repository] = lambda: repository
    try:
        response = TestClient(app).get(f'/analyses/{analysis.id}')
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    restored = response.json()
    from news_analysis.pipeline.models import FactCheckCriterionResult
    assert repository.get(analysis.id) == payload
    # HTTP responses include optional nulls absent from the stored JSON.
    expected_facts = FactCheckCriterionResult.model_validate(payload['criteria']['verifiable_facts']).model_dump(mode='json')
    assert restored['criteria']['verifiable_facts'] == expected_facts
    for key, value in source.items():
        assert restored['criteria']['source_credibility'][key] == value
    for key, value in payload['final'].items():
        assert restored['final'][key] == value
    assert restored['pipeline_version']['id'] == 'historical-v4'
    assert restored['final']['score_before_veto'] is None
    with closing(repository._connect()) as connection:
        assert connection.execute('SELECT payload_json FROM analyses WHERE id=?', (analysis.id,)).fetchone()[0] == raw
