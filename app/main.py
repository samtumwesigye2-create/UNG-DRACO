from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import database_ready, get_db
from app.models import AuditEvent, CollectionItem

app = FastAPI(title="UNG-DRACO", version="1.0.0")


class ObservationCreate(BaseModel):
    source_type: str = Field(min_length=1, max_length=64)
    domain: str = Field(min_length=1, max_length=32)
    platform: str | None = Field(default=None, max_length=128)
    location: dict | None = None
    raw_content: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


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
    correlation_id = str(uuid4())
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
        db.add(
            AuditEvent(
                actor_id="system:api",
                action="observation.created",
                resource_type="collection_item",
                resource_id=str(observation.id),
                correlation_id=correlation_id,
                result="success",
                request_metadata={
                    "source_type": payload.source_type,
                    "domain": payload.domain,
                    "event": "draco.observation.created",
                },
                created_at=datetime.now(timezone.utc),
            )
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
