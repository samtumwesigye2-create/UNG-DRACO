from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.security.rbac import Principal, require_roles
from app.video.capture import CaptureService
from app.video.control import ControlUnavailable, ManualCommand, ManualControlService
from app.video.models import StreamState
from app.video.sessions import VideoSessionManager
from app.video.signaling import IceCandidate, SessionDescription, SignalingService

router = APIRouter(prefix="/api/draco/v1/video", tags=["video"])
sessions = VideoSessionManager()
control_service: ManualControlService | None = None
signaling_service: SignalingService | None = None
capture_service: CaptureService | None = None

class SessionCreate(BaseModel): unit_id: str
class StateUpdate(BaseModel): state: StreamState
class ControlRequest(BaseModel): command: ManualCommand

def _owned(session_id: str, principal: Principal):
    try: session=sessions.get(session_id)
    except (KeyError,TimeoutError) as exc:
        raise HTTPException(status.HTTP_410_GONE if isinstance(exc,TimeoutError) else status.HTTP_404_NOT_FOUND,"video session unavailable") from exc
    if session.operator_id!=principal.subject and "draco_admin" not in principal.roles: raise HTTPException(status.HTTP_403_FORBIDDEN,"forbidden")
    return session

def _required(service, name: str):
    if service is None: raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,f"{name} unavailable")
    return service

@router.get("/status")
def video_status():
    return {
        "signaling": signaling_service is not None,
        "camera_control": control_service is not None,
        "capture": capture_service is not None,
        "operator_ready": signaling_service is not None,
    }

@router.post("/sessions",status_code=201)
def create_session(payload: SessionCreate,principal: Principal=Depends(require_roles("draco_operator","draco_admin"))): return sessions.create(payload.unit_id,principal.subject)

@router.get("/sessions/{session_id}")
def get_session(session_id: str,principal: Principal=Depends(require_roles("draco_operator","draco_admin"))): return _owned(session_id,principal)

@router.post("/sessions/{session_id}/state")
def update_state(session_id: str,payload: StateUpdate,principal: Principal=Depends(require_roles("draco_operator","draco_admin"))): _owned(session_id,principal); return sessions.mark_link(session_id,payload.state)

@router.post("/sessions/{session_id}/offer")
def offer(session_id: str,payload: SessionDescription,principal: Principal=Depends(require_roles("draco_operator","draco_admin"))):
    session=_owned(session_id,principal); return _required(signaling_service,"video signaling").accept_offer(session,payload)

@router.post("/sessions/{session_id}/ice",status_code=204)
def ice(session_id: str,payload: IceCandidate,principal: Principal=Depends(require_roles("draco_operator","draco_admin"))):
    session=_owned(session_id,principal); _required(signaling_service,"video signaling").add_ice_candidate(session,payload)

@router.post("/sessions/{session_id}/control")
def manual_control(session_id: str,payload: ControlRequest,principal: Principal=Depends(require_roles("draco_operator","draco_admin"))):
    session=_owned(session_id,principal); service=_required(control_service,"camera control")
    try: service.execute(session,payload.command)
    except ControlUnavailable as exc: raise HTTPException(status.HTTP_409_CONFLICT,"camera control unavailable") from exc
    return {"status":"accepted","command":payload.command}

@router.post("/sessions/{session_id}/snapshot")
def snapshot(session_id: str,principal: Principal=Depends(require_roles("draco_operator","draco_admin"))):
    return _required(capture_service,"capture").snapshot(_owned(session_id,principal))

@router.post("/sessions/{session_id}/recording/start")
def start_recording(session_id: str,principal: Principal=Depends(require_roles("draco_operator","draco_admin"))):
    rid=_required(capture_service,"capture").start_recording(_owned(session_id,principal)); return {"recording_id":rid,"status":"recording"}

@router.post("/sessions/{session_id}/recording/stop")
def stop_recording(session_id: str,principal: Principal=Depends(require_roles("draco_operator","draco_admin"))):
    rid=_required(capture_service,"capture").stop_recording(_owned(session_id,principal)); return {"recording_id":rid,"status":"stopped"}

@router.delete("/sessions/{session_id}",status_code=204)
def end_session(session_id: str,principal: Principal=Depends(require_roles("draco_operator","draco_admin"))): _owned(session_id,principal); sessions.expire(session_id)
