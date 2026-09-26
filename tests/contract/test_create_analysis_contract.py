from fastapi.testclient import TestClient

from news_analysis.api.app import app


def test_root_serves_link_analysis_interface():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert "Analisador de confiabilidade de noticias" in response.text
    assert 'id="analysis-form"' in response.text
    assert 'fetch("/analyses"' in response.text
    assert 'fetch("/config"' in response.text


def test_config_status_does_not_expose_secret():
    client = TestClient(app)
    response = client.get("/config")
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"fact_check_api_key_configured"}
    assert "test-key" not in response.text


def test_create_analysis_invalid_url_error_shape():
    client = TestClient(app)
    response = client.post("/analyses", json={"url": "not-a-url", "user_id": "contract-invalid"})
    assert response.status_code == 400
    payload = response.json()
    assert payload["status"] == "INVALID_URL"
    assert payload["error"]["code"] == "INVALID_URL"


def test_create_analysis_rejects_unknown_request_fields():
    client = TestClient(app)
    response = client.post("/analyses", json={"url": "https://example.com", "extra": True})
    assert response.status_code == 422
