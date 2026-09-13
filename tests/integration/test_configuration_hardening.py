from fastapi.testclient import TestClient

from app.main import app


def test_configured_identity_boundary_fails_closed_when_janus_missing(monkeypatch):
    monkeypatch.delenv("JANUS_ISSUER", raising=False)
    monkeypatch.delenv("JANUS_AUDIENCE", raising=False)
    monkeypatch.delenv("JANUS_JWKS_URL", raising=False)

    response = TestClient(app).get(
        "/v1/security/probe",
        headers={"Authorization": "Bearer placeholder-token"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "JANUS authentication is not configured"
