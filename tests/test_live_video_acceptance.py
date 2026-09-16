from pathlib import Path

from app.video.capture import CaptureService
from app.video.models import StreamState
from app.video.sessions import VideoSessionManager


class Capture:
    def snapshot(self,m): return {"unit_id":m.unit_id,"capture_type":m.capture_type}
    def start_recording(self,m): return "rec-1"
    def stop_recording(self,r): return True


def test_session_link_loss_and_recovery():
    manager=VideoSessionManager()
    session=manager.create("draco-mini-001","operator-1")
    manager.mark_link(session.session_id,StreamState.LINK_LOST)
    assert manager.get(session.session_id).state==StreamState.LINK_LOST
    manager.mark_link(session.session_id,StreamState.LIVE)
    assert manager.get(session.session_id).state==StreamState.LIVE


def test_snapshot_and_recording_lifecycle():
    manager=VideoSessionManager(); session=manager.create("draco-mini-001","operator-1")
    capture=CaptureService(Capture())
    assert capture.snapshot(session)["capture_type"]=="snapshot"
    assert capture.start_recording(session)=="rec-1"
    assert capture.stop_recording(session)=="rec-1"


def test_operator_console_contains_required_controls():
    html=Path("app/static/draco_operator.html").read_text()
    js=Path("app/static/draco_operator.js").read_text()
    for text in ["CONNECT","SNAPSHOT","START RECORDING","FULLSCREEN","LINK LOST"]: assert text in html
    for text in ["RTCPeerConnection","PAN_LEFT","PAN_RIGHT","TILT_UP","TILT_DOWN"]: assert text in js


def test_pi_agent_is_outbound_only():
    source=Path("device/draco_mini/video_agent.py").read_text()
    assert "devices/connect" in source
    assert "httpx.Client" in source
    assert "rpicam-vid" in source
    assert "FastAPI" not in source
