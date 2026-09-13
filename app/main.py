from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import database_ready, get_db
from app.models import AuditEvent, CollectionItem, Source, Watch

app = FastAPI(title="UNG-DRACO", version="1.0.0")


class ObservationCreate(BaseModel):
    source_type: str = Field(min_length=1, max_length=64)
    domain: str = Field(min_length=1, max_length=32)
    platform: str | None = Field(default=None, max_length=128)
    location: dict | None = None
    raw_content: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class SourceCreate(BaseModel):
    real_name: str = Field(min_length=1, max_length=255)
    contact: str | None = None
    notes: str | None = None


class WatchCreate(BaseModel):
    target: str = Field(min_length=1, max_length=255)
    target_type: str = Field(min_length=1, max_length=64)


def _audit(db: Session, action: str, resource_type: str, resource_id: str, metadata: dict | None = None) -> None:
    db.add(
        AuditEvent(
            actor_id="system:api",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            correlation_id=str(uuid4()),
            result="success",
            request_metadata=metadata,
            created_at=datetime.now(timezone.utc),
        )
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"system": "UNG-DRACO", "status": "ok"}


@app.get("/ready")
def ready(response: Response) -> dict[str, str]:
    if database_ready():
        return {"system": "UNG-DRACO", "status": "ready"}

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"system": "UNG-DRACO", "status": "not_ready"}


@app.post("/api/draco/v1/observations", status_code=status.HTTP_201_CREATED)
def create_observation(payload: ObservationCreate, db: Session = Depends(get_db)) -> dict[str, str]:
    observation = CollectionItem(
        source_type=payload.source_type,
        domain=payload.domain,
        platform=payload.platform,
        location=payload.location,
        raw_content=payload.raw_content,
        confidence=payload.confidence,
    )

    try:
        db.add(observation)
        db.flush()
        _audit(
            db,
            action="observation.created",
            resource_type="collection_item",
            resource_id=str(observation.id),
            metadata={
                "source_type": payload.source_type,
                "domain": payload.domain,
                "event": "draco.observation.created",
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "status": "accepted",
        "observation_id": str(observation.id),
        "event": "draco.observation.created",
    }


@app.post("/api/draco/v1/sources", status_code=status.HTTP_201_CREATED)
def create_source(payload: SourceCreate, db: Session = Depends(get_db)) -> dict[str, str]:
    source = Source(real_name=payload.real_name, contact=payload.contact, notes=payload.notes)
    try:
        db.add(source)
        db.flush()
        _audit(db, "source.registered", "source", str(source.id), {"real_name": payload.real_name})
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"status": "registered", "source_id": str(source.id)}


@app.get("/api/draco/v1/sources")
def list_sources(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Source).order_by(Source.created_at.asc())).all()
    return [
        {
            "id": str(item.id),
            "real_name": item.real_name,
            "contact": item.contact,
            "notes": item.notes,
        }
        for item in rows
    ]


@app.post("/api/draco/v1/watches", status_code=status.HTTP_201_CREATED)
def create_watch(payload: WatchCreate, db: Session = Depends(get_db)) -> dict:
    watch = Watch(target=payload.target, target_type=payload.target_type, active=True)
    try:
        db.add(watch)
        db.flush()
        _audit(
            db,
            "watch.created",
            "watch",
            str(watch.id),
            {"target": payload.target, "target_type": payload.target_type},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"watch_id": str(watch.id), "active": watch.active}


@app.get("/api/draco/v1/watches")
def list_watches(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Watch).order_by(Watch.created_at.asc())).all()
    return [
        {
            "id": str(item.id),
            "target": item.target,
            "target_type": item.target_type,
            "active": item.active,
            "start_date": item.start_date.isoformat() if item.start_date else None,
            "end_date": item.end_date.isoformat() if item.end_date else None,
        }
        for item in rows
    ]
