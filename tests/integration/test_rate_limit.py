from fastapi.testclient import TestClient

from news_analysis.api.app import app, rate_limiter


def test_rate_limit_rejects_eleventh_request_for_same_user():
    client = TestClient(app)
    rate_limiter.reset()
    for _ in range(10):
        assert client.post("/analyses", json={"url": "not-a-url", "user_id": "limited-user"}).status_code == 400
    response = client.post("/analyses", json={"url": "not-a-url", "user_id": "limited-user"})
    assert response.status_code == 429
    assert response.json()["status"] == "RATE_LIMITED"
