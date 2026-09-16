from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import uuid4

from app.video.models import StreamState, VideoSession


class SessionNotFound(KeyError):
    pass


class SessionExpired(RuntimeError):
    pass


class VideoSessionManager:
    def __init__(self, ttl: timedelta = timedelta(minutes=5), clock: Callable[[], datetime] | None = None):
        self.ttl = ttl
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._sessions: dict[str, VideoSession] = {}

    def create(self, unit_id: str, operator_id: str) -> VideoSession:
        now = self.clock()
        session = VideoSession(
            session_id=str(uuid4()),
            unit_id=unit_id,
            operator_id=operator_id,
            created_at=now,
            expires_at=now + self.ttl,
        )
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> VideoSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFound(session_id)
        if self.clock() >= session.expires_at:
            session.control_available = False
            raise SessionExpired(session_id)
        return session

    def expire(self, session_id: str) -> VideoSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFound(session_id)
        session.expires_at = self.clock()
        session.control_available = False
        return session

    def mark_link(self, session_id: str, state: StreamState) -> VideoSession:
        session = self.get(session_id)
        session.state = state
        session.control_available = state not in {StreamState.LINK_LOST, StreamState.CONNECTING}
        return session
