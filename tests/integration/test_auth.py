from fastapi.testclient import TestClient

from app.main import app


def test_health_remains_public():
    client = TestClient(app)
    assert client.get("/health").status_code == 200


def test_protected_probe_rejects_missing_identity():
    client = TestClient(app)
    response = client.get("/v1/security/probe")
    assert response.status_code == 401
