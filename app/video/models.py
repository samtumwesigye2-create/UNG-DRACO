from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class StreamState(StrEnum):
    ONLINE = "ONLINE"
    CONNECTING = "CONNECTING"
    LIVE = "LIVE"
    DEGRADED = "DEGRADED"
    LINK_LOST = "LINK LOST"


@dataclass
class VideoSession:
    session_id: str
    unit_id: str
    operator_id: str
    created_at: datetime
    expires_at: datetime
    state: StreamState = StreamState.CONNECTING
    control_available: bool = True
