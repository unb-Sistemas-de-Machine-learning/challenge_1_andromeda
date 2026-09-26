from fastapi.testclient import TestClient

from news_analysis.api.app import app


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
