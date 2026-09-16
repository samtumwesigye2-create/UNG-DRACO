from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from app.video.models import VideoSession


@dataclass(frozen=True)
class CaptureMetadata:
    unit_id: str
    timestamp: datetime
    operator_id: str
    session_id: str
    capture_type: str


class CaptureAdapter(Protocol):
    def snapshot(self, metadata: CaptureMetadata): ...
    def start_recording(self, metadata: CaptureMetadata): ...
    def stop_recording(self, recording_id: str): ...


class CaptureService:
    def __init__(self, adapter: CaptureAdapter):
        self.adapter = adapter
        self._recordings: dict[str, str] = {}

    def _metadata(self, session: VideoSession, capture_type: str) -> CaptureMetadata:
        return CaptureMetadata(
            unit_id=session.unit_id,
            timestamp=datetime.now(timezone.utc),
            operator_id=session.operator_id,
            session_id=session.session_id,
            capture_type=capture_type,
        )

    def snapshot(self, session: VideoSession):
        return self.adapter.snapshot(self._metadata(session, "snapshot"))

    def start_recording(self, session: VideoSession):
        if session.session_id in self._recordings:
            return self._recordings[session.session_id]
        recording_id = self.adapter.start_recording(self._metadata(session, "recording"))
        self._recordings[session.session_id] = recording_id
        return recording_id

    def stop_recording(self, session: VideoSession):
        recording_id = self._recordings.pop(session.session_id, None)
        if recording_id is None:
            return None
        self.adapter.stop_recording(recording_id)
        return recording_id
