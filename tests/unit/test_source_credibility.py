"""Source scoring tests use fictitious domains and no external network."""
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx

from news_analysis.criteria.credibility_config import CredibilityConfig
from news_analysis.criteria.credibility_io import SourceNetwork, load_domains, normalize_url
from news_analysis.criteria.source_credibility import SourceCredibility, domain_age, editorial_transparency


class Network:
    def __init__(self, days=3000, body='<html/>', final='https://example.com/article', failed=False):
        self.days, self.body, self.final, self.failed = days, body, final, failed
        self.calls = 0

    def fetch(self, url):
        return self.body, self.final

    def creation_date(self, domain):
        self.calls += 1
        if self.failed:
            raise TimeoutError('RDAP unavailable')
        return datetime.now(timezone.utc) - timedelta(days=self.days)


@pytest.fixture
def config(tmp_path):
    recognized, blocked = tmp_path / 'recognized.json', tmp_path / 'blocked.json'
    recognized.write_text('[]')
    blocked.write_text('[]')
    return CredibilityConfig(recognized_path=recognized, blocklist_path=blocked)


def test_new_domain(config):
    result = SourceCredibility(config, Network(days=10)).calculate('https://example.com')
    assert result['score_fonte'] == 5
    assert result['flags'] == ['dominio_recem_criado']
    assert result['veto_dominio_suspeito']


def test_old_domain_without_signals_is_capped(config):
    result = SourceCredibility(config, Network()).calculate('https://example.com')
    assert result['criterios'][2]['pontos'] == 8
    assert result['score_fonte'] == 13


def test_recognized_domain_gets_full_age(config):
    config.recognized_path.write_text('["example.com"]')
    result = SourceCredibility(config, Network()).calculate('https://example.com')
    assert result['score_fonte'] == 55


def test_gov_br(config):
    result = SourceCredibility(config, Network(final='https://ficticio.gov.br/article')).calculate('https://ficticio.gov.br')
    assert result['criterios'][3]['pontos'] == 20
    assert result['score_fonte'] == 33


def test_blocklist(config):
    config.blocklist_path.write_text('["example.com"]')
    result = SourceCredibility(config, Network()).calculate('https://example.com')
    assert result['score_fonte'] == 0
    assert 'dominio_em_lista_desinformacao' in result['flags']


def test_rdap_unavailable_normalizes(config):
    config.recognized_path.write_text('["example.com"]')
    result = SourceCredibility(config, Network(failed=True)).calculate('https://example.com')
    assert result['score_fonte'] == round(40 / 85 * 100)
    assert result['criterios'][2]['status'] == 'indisponivel'


def test_shortened_url(config):
    result = SourceCredibility(config, Network(final='https://example.com/article?utm_source=x&id=2')).calculate('https://example.org/short')
    assert result['url_final'] == 'https://example.com/article?id=2'
    assert result['dominio'] == 'example.com'


def test_page_specific_cache_and_domain_age(config):
    network = Network()
    scorer = SourceCredibility(config, network)
    scorer.calculate('https://example.com/a')
    network.body = '<meta name="author" content="Pessoa"><time datetime="2026-01-01"/>'
    result = scorer.calculate('https://example.com/b')
    assert result['criterios'][1]['pontos'] == 15
    assert result['criterios'][2]['pontos'] == 15
    assert network.calls == 1


def test_json_ld_and_same_domain_contact(config):
    body = '<script type="application/ld+json">' + json.dumps({'@graph': [{'@type': 'NewsArticle', 'author': {'name': 'Pessoa'}, 'datePublished': '2026-01-01'}]}) + '</script><a href="/contato">Contato</a>'
    assert editorial_transparency(body, 'https://example.com', config)['pontos'] == 25
    assert editorial_transparency('<a href="https://example.org/contato">Contato</a>', 'https://example.com', config)['pontos'] == 0


@pytest.mark.parametrize('days,points', [(0, 0), (30, 3), (183, 8), (730, 12), (1826, 15)])
def test_boundaries(days, points, config):
    now = datetime.now(timezone.utc)
    result, _ = domain_age(now - timedelta(days=days), True, 0, config, now)
    assert result['pontos'] == points


def test_total_network_failure(config):
    class Failed(Network):
        def fetch(self, url):
            raise httpx.ConnectError('offline')
    result = SourceCredibility(config, Failed()).calculate('https://example.com')
    assert result['confianca_fonte'] == 'baixa'
    assert all(c['status'] == 'indisponivel' for c in result['criterios'])
    assert result['erros']
    assert result['score_fonte'] is None
    assert result['veto_dominio_suspeito'] is False


def test_confirmed_blocklist_veto_survives_network_failure(config):
    class Failed(Network):
        def fetch(self, url):
            raise httpx.ConnectError('offline')
    config.blocklist_path.write_text('["example.com"]')
    result, evidence = SourceCredibility(config, Failed()).calculate_with_evidence('https://example.com')
    assert result['score_fonte'] == 0
    assert result['veto_dominio_suspeito'] is True
    assert evidence['veto']['reason_code'] == 'blocklist_match'
    assert evidence['blocklist']['matched_domains'] == ['example.com']


def test_blocklist_evidence_hashes_consulted_bytes_and_preserves_failures(config):
    import hashlib
    source = SourceCredibility(config, Network())
    _, original = source.calculate_with_evidence('https://example.com')
    assert original['blocklist']['content_hash'] == hashlib.sha256(config.blocklist_path.read_bytes()).hexdigest()
    config.blocklist_path.write_text('["example.com"]')
    _, updated = source.calculate_with_evidence('https://example.com')
    assert updated['blocklist']['content_hash'] != original['blocklist']['content_hash']
    assert updated['policy_hash'] == original['policy_hash']
    config.blocklist_path.write_text('invalid json')
    _, failed = source.calculate_with_evidence('https://example.com')
    assert failed['blocklist']['status'] == 'unavailable'
    assert failed['blocklist']['content_hash'] is None


def test_local_csv(tmp_path):
    path = tmp_path / 'sources.csv'
    path.write_text('dominio\nwww.example.com\n')
    assert load_domains(path) == {'example.com'}


@respx.mock
def test_network_redirect_and_rdap(monkeypatch, config):
    monkeypatch.setattr('news_analysis.criteria.credibility_io.assert_url_is_safe', lambda url: None)
    respx.get('https://example.org/s').mock(return_value=httpx.Response(302, headers={'location': 'https://example.com/a'}))
    respx.get('https://example.com/a').mock(return_value=httpx.Response(200, text='<html/>'))
    network = SourceNetwork(config)
    assert network.fetch('https://example.org/s')[1] == 'https://example.com/a'
    respx.get('https://rdap.registro.br/domain/ficticio.com.br').mock(return_value=httpx.Response(200, json={'events': [{'eventAction': 'registration', 'eventDate': '2020-01-01T00:00:00Z'}]}))
    assert network.creation_date('ficticio.com.br').year == 2020


def test_tracking_preserves_semantic_query():
    assert normalize_url('https://example.com/a?utm_medium=x&fbclid=y&id=1#top') == 'https://example.com/a?id=1'
