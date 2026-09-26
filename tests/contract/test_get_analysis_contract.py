from fastapi.testclient import TestClient

from news_analysis.api.app import app


def test_get_analysis_not_found_shape():
    response = TestClient(app).get("/analyses/missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
