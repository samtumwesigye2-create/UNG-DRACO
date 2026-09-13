from fastapi.testclient import TestClient

from app.database import engine
from app.main import app
from app.models import Base


def test_create_observation_persists_and_returns_identifier():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    client = TestClient(app)
    response = client.post(
        "/api/draco/v1/observations",
        json={
            "source_type": "sensor",
            "domain": "air",
            "platform": "SENSOR-017",
            "location": {"lat": 0.3136, "lon": 32.5811},
            "raw_content": "controlled synthetic aerial observation",
            "confidence": 0.82,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "accepted"
    assert body["observation_id"]
    assert body["event"] == "draco.observation.created"
