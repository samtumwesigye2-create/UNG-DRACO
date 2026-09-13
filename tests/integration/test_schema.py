from datetime import datetime, timezone

from sqlalchemy import select

from app.database import SessionLocal, engine
from app.models import (
    Alert,
    AuditEvent,
    Base,
    CollectionItem,
    Entity,
    IntelligenceProduct,
    Mission,
    Report,
    Source,
    Track,
    TrackItem,
    Watch,
)


def test_authoritative_domain_schema_persists_related_records():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    now = datetime.now(timezone.utc)

    with SessionLocal.begin() as session:
        source = Source(real_name="Protected Source", contact="protected@example.invalid")
        session.add(source)
        session.flush()

        report = Report(source_id=source.id, content="Observed convoy", reliability_rating=2)
        session.add(report)
        session.flush()

        item = CollectionItem(
            source_type="human_report",
            domain="ground",
            raw_content="Observed convoy",
            confidence=0.8,
            location={"name": "Sector A"},
            detection_score=0.72,
            detection_explanation={"evidence": ["report"]},
        )
        session.add(item)
        session.flush()

        entity = Entity(collection_item_id=item.id, type="organization", value="Convoy", normalized_value="convoy", confidence=0.9)
        mission = Mission(question="What is moving through Sector A?", target="Sector A", status="open")
        watch = Watch(target="Sector A", target_type="location", active=True)
        track = Track(status="active", confidence=0.77, fusion_explanation={"reason": "initial"})
        session.add_all([entity, mission, watch, track])
        session.flush()

        session.add(TrackItem(track_id=track.id, collection_item_id=item.id, match_score=0.81))
        session.add(Alert(watch_id=watch.id, track_id=track.id, match_reason="location", confidence=0.8, severity="medium", acknowledged=False))
        session.add(IntelligenceProduct(summary="Sector A activity", confidence=0.74, supporting_observations=[str(item.id)]))
        session.add(AuditEvent(actor_id="test-user", action="schema.test", resource_type="collection_item", resource_id=str(item.id), correlation_id="schema-test", result="success", created_at=now))

    with SessionLocal() as session:
        assert session.scalar(select(Source.real_name)) == "Protected Source"
        assert session.scalar(select(Report.content)) == "Observed convoy"
        assert session.scalar(select(CollectionItem.domain)) == "ground"
        assert session.scalar(select(Entity.normalized_value)) == "convoy"
        assert session.scalar(select(Mission.status)) == "open"
        assert session.scalar(select(Watch.active)) is True
        assert session.scalar(select(Track.status)) == "active"
        assert session.scalar(select(TrackItem.match_score)) == 0.81
        assert session.scalar(select(Alert.severity)) == "medium"
        assert session.scalar(select(IntelligenceProduct.summary)) == "Sector A activity"
        assert session.scalar(select(AuditEvent.correlation_id)) == "schema-test"
