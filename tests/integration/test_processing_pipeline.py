from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal, engine
from app.main import app
from app.models import Alert, AuditEvent, Base, CollectionItem, IntelligenceProduct, Track, Watch
from app.security.auth import get_current_principal
from app.security.rbac import Principal


def test_processing_pipeline_correlates_tracks_fuses_alerts_and_audits():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        first = CollectionItem(
            source_type="sensor",
            domain="air",
            platform="SENSOR-A",
            location={"lat": 0.3136, "lon": 32.5811},
            raw_content="synthetic observation A",
            confidence=0.82,
        )
        second = CollectionItem(
            source_type="sensor",
            domain="air",
            platform="SENSOR-B",
            location={"lat": 0.3140, "lon": 32.5815},
            raw_content="synthetic observation B",
            confidence=0.76,
        )
        watch = Watch(target="0.3136,32.5811", target_type="location", active=True)
        db.add_all([first, second, watch])
        db.commit()
        first_id = str(first.id)
        second_id = str(second.id)

    app.dependency_overrides[get_current_principal] = lambda: Principal(
        subject="analyst-acceptance", roles={"draco_analyst"}
    )
    try:
        client = TestClient(app)
        first_response = client.post(f"/api/draco/v1/observations/{first_id}/process")
        second_response = client.post(f"/api/draco/v1/observations/{second_id}/process")
    finally:
        app.dependency_overrides.clear()

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    with SessionLocal() as db:
        tracks = db.scalars(select(Track)).all()
        products = db.scalars(select(IntelligenceProduct)).all()
        alerts = db.scalars(select(Alert)).all()
        audits = db.scalars(select(AuditEvent)).all()

        assert len(tracks) == 1
        assert tracks[0].status in {"ACTIVE", "UPDATED"}
        assert len(products) >= 1
        assert any(
            {first_id, second_id}.issubset(set(product.supporting_observations))
            for product in products
        )
        assert len(alerts) == 1
        assert alerts[0].track_id == tracks[0].id
        actions = {event.action for event in audits}
        assert "track.processed" in actions
        assert "intelligence_product.created" in actions
        assert "alert.created" in actions
