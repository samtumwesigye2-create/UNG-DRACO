from fastapi.testclient import TestClient

from app.database import engine
from app.main import app
from app.models import Base


def test_create_and_list_sources_and_watches():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    client = TestClient(app)

    source_response = client.post(
        "/api/draco/v1/sources",
        json={
            "real_name": "Synthetic Sensor 017",
            "contact": "sensor017@example.invalid",
            "notes": "controlled acceptance source",
        },
    )
    assert source_response.status_code == 201
    source = source_response.json()
    assert source["source_id"]
    assert source["status"] == "registered"

    sources_response = client.get("/api/draco/v1/sources")
    assert sources_response.status_code == 200
    assert any(item["id"] == source["source_id"] for item in sources_response.json())

    watch_response = client.post(
        "/api/draco/v1/watches",
        json={"target": "Sector A", "target_type": "location"},
    )
    assert watch_response.status_code == 201
    watch = watch_response.json()
    assert watch["watch_id"]
    assert watch["active"] is True

    watches_response = client.get("/api/draco/v1/watches")
    assert watches_response.status_code == 200
    assert any(item["id"] == watch["watch_id"] for item in watches_response.json())
