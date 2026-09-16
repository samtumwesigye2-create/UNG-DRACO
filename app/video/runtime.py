import os
from dataclasses import dataclass
from uuid import uuid4

from app.video.capture import CaptureMetadata
from app.video.signaling import IceCandidate


@dataclass
class RuntimeConfig:
    public_base_url: str=os.getenv("DRACO_PUBLIC_URL","http://127.0.0.1:8000")
    turn_url: str=os.getenv("DRACO_TURN_URL","")
    turn_username: str=os.getenv("DRACO_TURN_USERNAME","")
    turn_credential: str=os.getenv("DRACO_TURN_CREDENTIAL","")


class RuntimePeerAdapter:
    """Adapter boundary for the deployed WebRTC media gateway."""
    def __init__(self): self.sessions={}
    def accept_offer(self,session_id: str,sdp: str)->str:
        gateway=self.sessions.get(session_id)
        if gateway is None: raise RuntimeError("DRACO media gateway has no connected unit for session")
        return gateway.accept_offer(sdp)
    def add_ice_candidate(self,session_id: str,candidate: IceCandidate)->None:
        gateway=self.sessions.get(session_id)
        if gateway is None: raise RuntimeError("DRACO media gateway has no connected unit for session")
        gateway.add_ice_candidate(candidate)


class RuntimeCaptureAdapter:
    def __init__(self): self.units={}
    def _unit(self,metadata: CaptureMetadata):
        unit=self.units.get(metadata.unit_id)
        if unit is None: raise RuntimeError("DRACO unit unavailable")
        return unit
    def snapshot(self,metadata: CaptureMetadata): return self._unit(metadata).snapshot(metadata)
    def start_recording(self,metadata: CaptureMetadata): return self._unit(metadata).start_recording(metadata) or str(uuid4())
    def stop_recording(self,recording_id: str):
        for unit in self.units.values():
            if unit.stop_recording(recording_id): return


class RuntimeControlAdapter:
    def __init__(self): self.units={}
    def send(self,unit_id: str,command):
        unit=self.units.get(unit_id)
        if unit is None: raise RuntimeError("DRACO unit unavailable")
        unit.send_control(command)
