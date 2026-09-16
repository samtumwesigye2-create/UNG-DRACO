from enum import StrEnum
from typing import Protocol

from app.video.models import VideoSession


class ManualCommand(StrEnum):
    PAN_LEFT = "PAN_LEFT"
    PAN_RIGHT = "PAN_RIGHT"
    TILT_UP = "TILT_UP"
    TILT_DOWN = "TILT_DOWN"
    CENTER = "CENTER"
    STOP = "STOP"


class ControlUnavailable(RuntimeError):
    pass


class ServoAdapter(Protocol):
    def execute(self, command: ManualCommand) -> None: ...


class ManualControlService:
    def __init__(self, servo: ServoAdapter):
        self.servo = servo

    def execute(self, session: VideoSession, command: ManualCommand) -> None:
        if not session.control_available:
            raise ControlUnavailable("camera control channel unavailable")
        self.servo.execute(command)
