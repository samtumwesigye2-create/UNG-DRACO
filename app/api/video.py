from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.security.rbac import Principal, require_roles
from app.video.control import ControlUnavailable, ManualCommand, ManualControlService
from app.video.models import StreamState
from app.video.sessions import VideoSessionManager

router = APIRouter(prefix="/api/draco/v1/video", tags=["video"])
sessions = VideoSessionManager()
control_service: ManualControlService | None = None


class SessionCreate(BaseModel):
    unit_id: str


class StateUpdate(BaseModel):
    state: StreamState


class ControlRequest(BaseModel):
    command: ManualCommand


def _owned(session_id: str, principal: Principal):
    try:
        session = sessions.get(session_id)
    except (KeyError, TimeoutError) as exc:
        code = status.HTTP_410_GONE if isinstance(exc, TimeoutError) else status.HTTP_404_NOT_FOUND
        raise HTTPException(code, "video session unavailable") from exc
    if session.operator_id != principal.subject and "draco_admin" not in principal.roles:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden")
    return session


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreate,
    principal: Principal = Depends(require_roles("draco_operator", "draco_admin")),
):
    return sessions.create(payload.unit_id, principal.subject)


@router.get("/sessions/{session_id}")
def get_session(
    session_id: str,
    principal: Principal = Depends(require_roles("draco_operator", "draco_admin")),
):
    return _owned(session_id, principal)


@router.post("/sessions/{session_id}/state")
def update_state(
    session_id: str,
    payload: StateUpdate,
    principal: Principal = Depends(require_roles("draco_operator", "draco_admin")),
):
    _owned(session_id, principal)
    return sessions.mark_link(session_id, payload.state)


@router.post("/sessions/{session_id}/control")
def manual_control(
    session_id: str,
    payload: ControlRequest,
    principal: Principal = Depends(require_roles("draco_operator", "draco_admin")),
):
    session = _owned(session_id, principal)
    if control_service is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "camera control adapter unavailable")
    try:
        control_service.execute(session, payload.command)
    except ControlUnavailable as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "camera control unavailable") from exc
    return {"status": "accepted", "command": payload.command}


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def end_session(
    session_id: str,
    principal: Principal = Depends(require_roles("draco_operator", "draco_admin")),
):
    _owned(session_id, principal)
    sessions.expire(session_id)
