from fastapi.testclient import TestClient

from app.database import engine
from app.main import app
from app.models import Base
from app.security.auth import get_current_principal
from app.security.rbac import Principal


def _as(subject: str, *roles: str):
    app.dependency_overrides[get_current_principal] = lambda: Principal(subject=subject, roles=set(roles))


def test_draco_end_to_end_operational_acceptance():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    try:
        _as("source-admin", "draco_source_admin")
        source = client.post(
            "/api/draco/v1/sources",
            json={"real_name": "Protected Source Alpha", "contact": "restricted", "notes": "acceptance"},
        )
        assert source.status_code == 201

        _as("analyst", "draco_analyst")
        watch = client.post(
            "/api/draco/v1/watches",
            json={"target": "0.3476,32.5825", "target_type": "location"},
        )
        assert watch.status_code == 201

        _as("collector", "draco_collector")
        observation_ids = []
        for platform, lat, confidence in (("sensor-a", 0.3476, 0.90), ("sensor-b", 0.3480, 0.86)):
            response = client.post(
                "/api/draco/v1/observations",
                json={
                    "source_type": "sensor",
                    "domain": "air",
                    "platform": platform,
                    "location": {"lat": lat, "lon": 32.5825},
                    "raw_content": "correlated acceptance observation",
                    "confidence": confidence,
                },
            )
            assert response.status_code == 201
            observation_ids.append(response.json()["observation_id"])

        _as("analyst", "draco_analyst")
        first = client.post(f"/api/draco/v1/observations/{observation_ids[0]}/process")
        second = client.post(f"/api/draco/v1/observations/{observation_ids[1]}/process")
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["track_id"] == second.json()["track_id"]

        tracks = client.get("/api/draco/v1/tracks").json()
        products = client.get("/api/draco/v1/products").json()
        alerts = client.get("/api/draco/v1/alerts").json()
        audit = client.get("/api/draco/v1/audit").json()

        assert len(tracks) == 1
        assert tracks[0]["status"] in {"ACTIVE", "UPDATED"}
        assert set(tracks[0]["observation_ids"]) == set(observation_ids)
        assert any(set(product["supporting_observations"]) == set(observation_ids) for product in products)
        assert len(alerts) >= 1
        assert alerts[0]["track_id"] == tracks[0]["id"]

        actions = {event["action"] for event in audit}
        assert {
            "source.registered",
            "observation.created",
            "track.processed",
            "intelligence_product.created",
            "alert.created",
        }.issubset(actions)

        observations = client.get("/api/draco/v1/observations").json()
        assert len(observations) == 2
        assert all("real_name" not in item and "contact" not in item and "notes" not in item for item in observations)
    finally:
        app.dependency_overrides.clear()
