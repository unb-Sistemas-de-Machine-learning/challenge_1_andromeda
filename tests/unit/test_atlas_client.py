"""Contract fixtures use public sanitized samples; transport is fully mocked."""
import json
from dataclasses import replace
from pathlib import Path

import httpx
import pytest

from news_analysis.criteria.atlas_client import AtlasClient, AtlasError
from news_analysis.criteria.credibility_config import AtlasConfig

BASE = 'https://api.atlas.jor.br/api/v1'
BBC = json.loads(Path('tests/fixtures/atlas/bbc_real.json').read_text(encoding='utf-8'))


def record(url='https://news.example.com', **updates):
    return {**BBC, 'media_channels': [{'channel_id': 1, 'link': url, 'channel': {'id': 1, 'name': 'Site'}}], **updates}


def client_for(rows, config=None, responses=None, resolver=None):
    requests = []
    def handler(request):
        requests.append(request)
        if responses:
            response = responses(request)
            if response is not None:
                return response
        if request.url.path.endswith('dummy-jwt'):
            return httpx.Response(200, json={'access_token': 'secret-token', 'expires_in': 3600})
        if request.url.path.endswith('definitions'):
            return httpx.Response(200, json=['id', 'nome_veiculo', 'segmento', 'ativo', 'eh_jornal', 'data_fechamento'])
        return httpx.Response(200, json=rows)
    client = AtlasClient(config or AtlasConfig(enabled=True), httpx.Client(transport=httpx.MockTransport(handler)), resolver=resolver)
    return client, requests


def test_real_site_contract_and_redirect_evidence():
    client, calls = client_for([BBC], resolver=lambda url, deadline: [url, 'https://bbcbrasil.com/', 'https://www.bbc.com/portuguese'])
    result = client.collect()
    assert {link['domain'] for link in result['links']} == {'bbcbrasil.com', 'bbc.com'}
    assert all(link['atlas_id'] == 14205 for link in result['links'])
    assert all(link['official_url'] == BBC['media_channels'][0]['link'] for link in result['links'])
    assert 'secret-token' not in json.dumps(result)
    assert not any('email' in k for k in result)
    assert 'field%5B%5D' in str(calls[-1].url)


def test_reuses_token_and_filters_inactive_and_shared_hosts():
    client, calls = client_for([record(), record(id=2, ativo=0), record('https://tenant.blogspot.com', id=3)])
    result = client.collect()
    assert len(result['links']) == 1
    assert not result['identity_complete']
    client.collect()
    assert sum(r.url.path.endswith('dummy-jwt') for r in calls) == 1


@pytest.mark.parametrize('status', [403, 429, 503])
def test_http_errors_are_sanitized_and_bounded(status):
    client, calls = client_for([], config=replace(AtlasConfig(enabled=True), retries=0),
        responses=lambda req: httpx.Response(status, text='secret-token private email') if req.url.path.endswith('analytic') else None)
    with pytest.raises(AtlasError) as error:
        client.collect()
    assert error.value.code == f'http_{status}'
    assert 'secret-token' not in str(error.value)


def test_401_refreshes_once():
    seen = 0
    def responses(req):
        nonlocal seen
        if req.url.path.endswith('analytic'):
            seen += 1
            if seen <= 2:
                return httpx.Response(401)
    client, calls = client_for([record()], responses=responses)
    with pytest.raises(AtlasError) as error:
        client.collect()
    assert error.value.code == 'http_401'
    assert seen == 2


@pytest.mark.parametrize('rows', [{"data": [], "next_page_url": "https://evil.test"}, [], [{'id': 1}], [record(media_channels='bad')]])
def test_invalid_or_empty_contract_is_rejected(rows):
    client, _ = client_for(rows)
    with pytest.raises(AtlasError):
        client.collect()


def test_credentialed_site_is_not_evidence():
    client, _ = client_for([record('https://user:password@example.com'), record('https://valid.example.net', id=2)])
    result = client.collect()
    assert len(result['links']) == 1
    assert result['exclusion_reasons']['invalid_site_url'] == 1


def test_no_cross_origin_auth_redirect():
    client, calls = client_for([], responses=lambda req: httpx.Response(302, headers={'location': 'https://evil.example.com'}) if req.url.path.endswith('analytic') else None)
    with pytest.raises(AtlasError):
        client.collect()
    assert all(r.url.host == 'api.atlas.jor.br' for r in calls)


@pytest.mark.parametrize('problem,expected', [('invalid_json', 'invalid_json'), ('size', 'response_too_large'), ('transport', 'transport_error')])
def test_transport_contract_limits(problem, expected):
    def responses(req):
        if req.url.path.endswith('analytic'):
            if problem == 'transport':
                raise httpx.ReadTimeout('sensitive remote detail', request=req)
            return httpx.Response(200, content=b'not-json' if problem == 'invalid_json' else b'x' * 1000)
    config = replace(AtlasConfig(enabled=True), retries=0, max_bytes=200)
    client, _ = client_for([record()], config=config, responses=responses)
    with pytest.raises(AtlasError) as error:
        client.collect()
    assert error.value.code == expected


def test_retry_after_does_not_retry_early():
    config = replace(AtlasConfig(enabled=True), sync_budget=1)
    client, calls = client_for([], config=config, responses=lambda req:
        httpx.Response(429, headers={'Retry-After': '120'}) if req.url.path.endswith('analytic') else None)
    with pytest.raises(AtlasError) as error:
        client.collect()
    assert error.value.code == 'sync_budget_exceeded'
    assert sum(r.url.path.endswith('analytic') for r in calls) == 1


def test_auth_expiration_and_missing_date_are_rejected():
    client, _ = client_for([record()], responses=lambda req:
        httpx.Response(200, json={'access_token': 'secret', 'expires_in': 'NaN'}) if req.url.path.endswith('dummy-jwt') else None)
    with pytest.raises(AtlasError, match='invalid_auth_response'):
        client.collect()


def test_bounded_redirect_resolver_never_uses_jwt(monkeypatch):
    import respx
    from time import monotonic
    monkeypatch.setattr('news_analysis.criteria.atlas_client.assert_url_is_safe', lambda url: None)
    with respx.mock:
        first = respx.get('https://t.co/demo').mock(return_value=httpx.Response(301, headers={'location': 'https://www.example.com/news'}))
        last = respx.get('https://www.example.com/news').mock(return_value=httpx.Response(200))
        client = AtlasClient(AtlasConfig(enabled=True))
        client.token = 'secret-token'
        try:
            chain = client.resolve_site('https://t.co/demo', monotonic() + 10)
            assert chain == ['https://t.co/demo', 'https://www.example.com/news']
            assert 'Authorization' not in first.calls[0].request.headers
            assert 'Authorization' not in last.calls[0].request.headers
        finally:
            client.close()


def test_redirect_to_private_network_is_blocked():
    import respx
    from time import monotonic
    with respx.mock:
        client = AtlasClient(AtlasConfig(enabled=True))
        try:
            with pytest.raises(Exception):
                client.resolve_site('http://127.0.0.1/site', monotonic() + 5)
        finally:
            client.close()
