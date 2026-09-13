from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, AuditEvent, CollectionItem, IntelligenceProduct, Track, TrackItem
from app.security.rbac import Principal, require_roles

router = APIRouter(prefix="/api/draco/v1", tags=["operations"])


def _iso(value):
    return value.isoformat() if value else None


@router.get("/observations")
def list_observations(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("draco_analyst", "draco_admin")),
) -> list[dict]:
    rows = db.scalars(select(CollectionItem).order_by(CollectionItem.created_at.asc())).all()
    return [
        {
            "id": str(item.id),
            "source_type": item.source_type,
            "domain": item.domain,
            "platform": item.platform,
            "location": item.location,
            "confidence": item.confidence,
            "target_acquired": item.target_acquired,
            "target_type": item.target_type,
            "extraction_status": item.extraction_status,
            "detection_score": item.detection_score,
            "created_at": _iso(item.created_at),
            "updated_at": _iso(item.updated_at),
        }
        for item in rows
    ]


@router.get("/tracks")
def list_tracks(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("draco_analyst", "draco_admin")),
) -> list[dict]:
    rows = db.scalars(select(Track).order_by(Track.created_at.asc())).all()
    output = []
    for item in rows:
        observation_ids = [
            str(value)
            for value in db.scalars(
                select(TrackItem.collection_item_id)
                .where(TrackItem.track_id == item.id)
                .order_by(TrackItem.created_at.asc())
            ).all()
        ]
        output.append(
            {
                "id": str(item.id),
                "status": item.status,
                "confidence": item.confidence,
                "location": item.location,
                "target_type": item.target_type,
                "fusion_explanation": item.fusion_explanation,
                "observation_ids": observation_ids,
                "created_at": _iso(item.created_at),
                "updated_at": _iso(item.updated_at),
            }
        )
    return output


@router.get("/alerts")
def list_alerts(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("draco_analyst", "draco_admin")),
) -> list[dict]:
    rows = db.scalars(select(Alert).order_by(Alert.created_at.asc())).all()
    return [
        {
            "id": str(item.id),
            "watch_id": str(item.watch_id),
            "collection_item_id": str(item.collection_item_id) if item.collection_item_id else None,
            "track_id": str(item.track_id) if item.track_id else None,
            "match_reason": item.match_reason,
            "confidence": item.confidence,
            "severity": item.severity,
            "acknowledged": item.acknowledged,
            "created_at": _iso(item.created_at),
            "updated_at": _iso(item.updated_at),
        }
        for item in rows
    ]


@router.get("/products")
def list_products(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("draco_analyst", "draco_admin")),
) -> list[dict]:
    rows = db.scalars(select(IntelligenceProduct).order_by(IntelligenceProduct.created_at.asc())).all()
    return [
        {
            "id": str(item.id),
            "summary": item.summary,
            "confidence": item.confidence,
            "supporting_observations": item.supporting_observations,
            "related_entities": item.related_entities,
            "related_tracks": item.related_tracks,
            "watch_matches": item.watch_matches,
            "mission_relevance": item.mission_relevance,
            "analyst_review_flags": item.analyst_review_flags,
            "created_at": _iso(item.created_at),
            "updated_at": _iso(item.updated_at),
        }
        for item in rows
    ]


@router.get("/audit")
def list_audit_events(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("draco_analyst", "draco_admin")),
) -> list[dict]:
    rows = db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.asc())).all()
    return [
        {
            "id": str(item.id),
            "actor_id": item.actor_id,
            "action": item.action,
            "resource_type": item.resource_type,
            "resource_id": item.resource_id,
            "correlation_id": item.correlation_id,
            "result": item.result,
            "request_metadata": item.request_metadata,
            "created_at": _iso(item.created_at),
        }
        for item in rows
    ]
