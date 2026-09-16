from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.security.audit import append_audit_event
from app.security.auth import get_current_principal
from app.security.rbac import Principal, require_roles
from app.services.traffic_enforcement import build_traffic_observation

router = APIRouter(prefix="/api/draco/v1/traffic", tags=["traffic observation"])


class TrafficAnalysisRequest(BaseModel):
    unit_id: str = Field(min_length=1, max_length=128)
    plate_text: str | None = Field(default=None, max_length=32)
    plate_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    speed_kmh: float | None = Field(default=None, ge=0.0)
    direction_deg: float | None = Field(default=None, ge=0.0, lt=360.0)
    direction_label: str | None = Field(default=None, max_length=8)
    detector_flags: list[str] = Field(default_factory=list, max_length=32)
    configured_speed_threshold_kmh: float | None = Field(default=None, gt=0.0)


@router.post("/analyze")
def analyze_traffic_observation(
    payload: TrafficAnalysisRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("draco_operator", "draco_analyst", "draco_admin")),
) -> dict:
    result = build_traffic_observation(
        plate_text=payload.plate_text,
        plate_confidence=payload.plate_confidence,
        speed_kmh=payload.speed_kmh,
        direction_deg=payload.direction_deg,
        direction_label=payload.direction_label,
        detector_flags=payload.detector_flags,
        configured_speed_threshold_kmh=payload.configured_speed_threshold_kmh,
    )
    correlation_id = str(uuid4())
    append_audit_event(
        db,
        actor_id=principal.subject,
        action="traffic.observation.analyzed",
        resource_type="draco_unit",
        resource_id=payload.unit_id,
        correlation_id=correlation_id,
        result="success",
        request_metadata={
            "event": "draco.traffic.observation.analyzed",
            "flags": list(result.detection_flags),
            "review_required": True,
        },
    )
    db.commit()
    return {
        "status": "PENDING_REVIEW",
        "unit_id": payload.unit_id,
        "correlation_id": correlation_id,
        "observation": result.to_dict(),
    }
