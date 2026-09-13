from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent


def append_audit_event(
    db: Session,
    *,
    actor_id: str,
    action: str,
    resource_type: str,
    correlation_id: str,
    result: str,
    resource_id: str | None = None,
    request_metadata: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        correlation_id=correlation_id,
        result=result,
        request_metadata=request_metadata,
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    db.flush()
    return event
