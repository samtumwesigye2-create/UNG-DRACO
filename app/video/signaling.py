from typing import Protocol

from pydantic import BaseModel

from app.video.models import VideoSession


class IceServer(BaseModel):
    urls: list[str]
    username: str | None = None
    credential: str | None = None


class SessionDescription(BaseModel):
    type: str
    sdp: str


class IceCandidate(BaseModel):
    candidate: str
    sdpMid: str | None = None
    sdpMLineIndex: int | None = None


class SignalingResult(BaseModel):
    answer: SessionDescription
    ice_servers: list[IceServer]


class PeerAdapter(Protocol):
    def accept_offer(self, session_id: str, sdp: str) -> str: ...
    def add_ice_candidate(self, session_id: str, candidate: IceCandidate) -> None: ...


class SignalingService:
    def __init__(self, peer: PeerAdapter, ice_servers: list[IceServer] | None = None):
        self.peer = peer
        self.ice_servers = ice_servers or []

    def accept_offer(self, session: VideoSession, offer: SessionDescription) -> SignalingResult:
        answer_sdp = self.peer.accept_offer(session.session_id, offer.sdp)
        return SignalingResult(
            answer=SessionDescription(type="answer", sdp=answer_sdp),
            ice_servers=self.ice_servers,
        )

    def add_ice_candidate(self, session: VideoSession, candidate: IceCandidate) -> None:
        self.peer.add_ice_candidate(session.session_id, candidate)
