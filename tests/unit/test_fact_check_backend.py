import asyncio
import json

import httpx
import pytest
from fastapi import HTTPException

from backend.main import FactCheckRequest, fact_check
from news_analysis.config import Settings
from news_analysis.criteria.fact_check import FactCheckClient


def test_proxy_forwards_project_parameters_and_raw_response(monkeypatch):
    monkeypatch.setenv("GOOGLE_FACT_CHECK_API_KEY", "google-secret")
    monkeypatch.setenv("FACTCHECK_PROXY_TOKEN", "proxy-secret")
    seen = []

    def google(request):
        seen.append(request)
        return httpx.Response(200, json={"claims": [{"text": "checagem"}], "nextPageToken": "next"},
                              request=request)

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, params):
            return google(httpx.Request("GET", url, params=params))

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: Client())
    payload = asyncio.run(fact_check(
        FactCheckRequest(query="Vacina reduz casos graves", pageToken="previous"),
        authorization="Bearer proxy-secret",
    ))
    assert payload == {"claims": [{"text": "checagem"}], "nextPageToken": "next"}
    assert dict(seen[0].url.params) == {
        "query": "Vacina reduz casos graves", "pageSize": "10", "languageCode": "pt",
        "pageToken": "previous", "key": "google-secret",
    }


def test_proxy_rejects_unauthorized_and_sanitizes_google_errors(monkeypatch):
    monkeypatch.setenv("GOOGLE_FACT_CHECK_API_KEY", "google-secret")
    monkeypatch.setenv("FACTCHECK_PROXY_TOKEN", "proxy-secret")
    with pytest.raises(HTTPException) as unauthorized:
        asyncio.run(fact_check(FactCheckRequest(query="vacina"), authorization=None))
    assert unauthorized.value.status_code == 401

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, params):
            return httpx.Response(429, text="google-secret", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: Client())
    with pytest.raises(HTTPException) as error:
        asyncio.run(fact_check(FactCheckRequest(query="vacina"), authorization="Bearer proxy-secret"))
    assert error.value.status_code == 429
    assert "google-secret" not in error.value.detail


def test_existing_client_uses_proxy_and_paginates():
    requests = []

    def proxy(request):
        requests.append(request)
        assert request.headers["authorization"] == "Bearer proxy-secret"
        if len(requests) == 1:
            return httpx.Response(200, json={"claims": [{"text": "first"}], "nextPageToken": "next"})
        return httpx.Response(200, json={"claims": [{"text": "second"}]})

    settings = Settings(factcheck_backend_url="https://proxy.example", factcheck_proxy_token="proxy-secret")
    with httpx.Client(transport=httpx.MockTransport(proxy)) as client:
        result = FactCheckClient(settings, client).search("vacina")
    assert len(result["claims"]) == 2
    assert all(request.method == "POST" for request in requests)
    assert all(request.url == "https://proxy.example/fact-check" for request in requests)
    assert json.loads(requests[1].content) == {
        "query": "vacina", "pageSize": 10, "languageCode": "pt", "pageToken": "next",
    }
    assert b"key" not in requests[0].content
