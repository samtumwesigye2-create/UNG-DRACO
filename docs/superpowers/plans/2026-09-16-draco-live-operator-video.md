# DRACO Gen-1 Live Operator Video Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build secure browser-based remote live video for DRACO-Mini with short-lived authorized sessions, WebRTC signaling, safe manual pan/tilt, snapshots, operator-controlled recording, reconnect states, and audit coverage.

**Architecture:** Keep the Pi non-public and outbound-only. Add focused FastAPI session/signaling/control/capture boundaries to the existing DRACO service and a browser console that negotiates WebRTC; TURN configuration is returned only to authorized short-lived sessions. Hardware-facing camera and servo operations sit behind adapters so CI uses deterministic fakes.

**Tech Stack:** Python 3, FastAPI 0.115.12, Pydantic 2.11.3, SQLAlchemy 2.0.40, PyJWT 2.10.1, pytest 8.3.5, browser JavaScript WebRTC APIs, Raspberry Pi rpicam/H.264 at deployment.

**Spec:** `docs/superpowers/specs/2026-09-16-draco-live-operator-video-design.md`

## Global Constraints

- Default Gen-1 video profile is 720p at 30 fps and optimized for low latency.
- DRACO-Mini initiates outbound connections; do not expose a public inbound camera port.
- Operator access uses the existing DRACO authentication/RBAC boundary.
- Viewing sessions are short-lived and bound to one operator and one DRACO unit.
- Video and manual control are separate logical channels; stale movement commands must never be queued after control loss.
- Recording is off by default and begins only on explicit authorized operator action.
- CI must not require physical Raspberry Pi, camera, servo, TURN, or browser hardware.
- No autonomous tracking, targeting, weapon interfaces, firing controls, laser designation, or autonomous engagement.

---

## File Structure

- `app/video/models.py` — session/state/value types.
- `app/video/sessions.py` — short-lived session lifecycle and authorization-independent domain rules.
- `app/video/signaling.py` — WebRTC offer/answer/ICE exchange contract and TURN configuration boundary.
- `app/video/control.py` — bounded manual pan/tilt command validation and link-loss interlock.
- `app/video/capture.py` — snapshot/record lifecycle interface and metadata.
- `app/video/adapters.py` — fake/production-facing camera, servo, and signaling adapter protocols.
- `app/api/video.py` — authenticated FastAPI endpoints and audit integration.
- `app/static/draco_operator.html` — browser operator console.
- `app/static/draco_operator.js` — WebRTC negotiation, stream-state UI, reconnect, and controls.
- `tests/unit/test_video_sessions.py` — session expiry/state rules.
- `tests/unit/test_video_control.py` — manual-control interlocks.
- `tests/unit/test_video_capture.py` — snapshot/record behavior.
- `tests/integration/test_video_api.py` — RBAC, signaling, audit, and endpoint behavior.
- `tests/unit/test_operator_console_contract.py` — static console contract without requiring a browser.

---

### Task 1: Session and stream-state domain

**Files:**
- Create: `app/video/__init__.py`
- Create: `app/video/models.py`
- Create: `app/video/sessions.py`
- Test: `tests/unit/test_video_sessions.py`

**Interfaces:**
- Produces: `StreamState`, `VideoSession`, `VideoSessionManager.create(unit_id, operator_id)`, `get(session_id)`, `expire(session_id)`, and `mark_link(session_id, state)`.
- `VideoSession` contains `session_id`, `unit_id`, `operator_id`, `created_at`, `expires_at`, `state`, and `control_available`.

- [ ] **Step 1: Write failing session tests**

```python
from datetime import datetime, timedelta, timezone

from app.video.models import StreamState
from app.video.sessions import VideoSessionManager


def test_session_is_bound_to_unit_operator_and_expires():
    now = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
    manager = VideoSessionManager(ttl=timedelta(minutes=5), clock=lambda: now)
    session = manager.create("draco-mini-001", "operator-7")
    assert session.unit_id == "draco-mini-001"
    assert session.operator_id == "operator-7"
    assert session.expires_at == now + timedelta(minutes=5)
    assert session.state is StreamState.CONNECTING


def test_link_loss_disables_control():
    manager = VideoSessionManager()
    session = manager.create("draco-mini-001", "operator-7")
    manager.mark_link(session.session_id, StreamState.LINK_LOST)
    assert manager.get(session.session_id).control_available is False
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `pytest -q tests/unit/test_video_sessions.py`
Expected: FAIL because `app.video.models` and `app.video.sessions` do not exist.

- [ ] **Step 3: Implement the minimal session model and manager**

```python
# app/video/models.py
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
    state: StreamState
    control_available: bool
```

Implement `VideoSessionManager` with a five-minute default TTL, UTC clock injection, UUID session IDs, expiry checks in `get`, and `control_available=False` for `LINK_LOST` or expired sessions.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `pytest -q tests/unit/test_video_sessions.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/video tests/unit/test_video_sessions.py
git commit -m "feat: add DRACO video session domain"
```

---

### Task 2: WebRTC signaling contract

**Files:**
- Create: `app/video/signaling.py`
- Create: `app/video/adapters.py`
- Test: `tests/unit/test_video_signaling.py`

**Interfaces:**
- Consumes: active `VideoSession` from Task 1.
- Produces: `IceServer`, `SessionDescription`, `SignalingService.accept_offer(session, offer)`, and `add_ice_candidate(session, candidate)`.

- [ ] **Step 1: Write failing signaling tests**

```python
from app.video.signaling import IceServer, SessionDescription, SignalingService

class FakePeer:
    def accept_offer(self, session_id, sdp):
        return "answer-sdp"
    def add_ice_candidate(self, session_id, candidate):
        self.candidate = candidate


def test_offer_returns_answer_and_turn_configuration(active_session):
    service = SignalingService(
        peer=FakePeer(),
        ice_servers=[IceServer(urls=["turn:relay.example.test:3478"], username="u", credential="c")],
    )
    result = service.accept_offer(active_session, SessionDescription(type="offer", sdp="offer-sdp"))
    assert result.answer.sdp == "answer-sdp"
    assert result.ice_servers[0].urls == ["turn:relay.example.test:3478"]
```

- [ ] **Step 2: Run and verify RED**

Run: `pytest -q tests/unit/test_video_signaling.py`
Expected: FAIL because signaling types/service do not exist.

- [ ] **Step 3: Implement signaling types and adapter protocol**

Use Pydantic models for `IceServer`, `SessionDescription`, `IceCandidate`, and `SignalingResult`. Define a `PeerAdapter` protocol in `adapters.py`. `accept_offer` rejects an expired session, delegates SDP handling to the adapter, and returns the answer plus configured ICE servers.

- [ ] **Step 4: Run and verify GREEN**

Run: `pytest -q tests/unit/test_video_signaling.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/video/signaling.py app/video/adapters.py tests/unit/test_video_signaling.py
git commit -m "feat: add DRACO WebRTC signaling contract"
```

---

### Task 3: Manual pan/tilt safety interlock

**Files:**
- Create: `app/video/control.py`
- Modify: `app/video/adapters.py`
- Test: `tests/unit/test_video_control.py`

**Interfaces:**
- Consumes: `VideoSession.control_available`.
- Produces: `ManualControlService.execute(session, command)` and `ServoAdapter.execute(command)`.
- Commands are exactly `PAN_LEFT`, `PAN_RIGHT`, `TILT_UP`, `TILT_DOWN`, `CENTER`, `STOP`.

- [ ] **Step 1: Write failing control tests**

```python
import pytest
from app.video.control import ControlUnavailable, ManualCommand, ManualControlService

class FakeServo:
    def __init__(self): self.commands = []
    def execute(self, command): self.commands.append(command)


def test_link_lost_rejects_movement(link_lost_session):
    servo = FakeServo()
    service = ManualControlService(servo)
    with pytest.raises(ControlUnavailable):
        service.execute(link_lost_session, ManualCommand.PAN_LEFT)
    assert servo.commands == []


def test_active_control_executes_immediately(active_session):
    servo = FakeServo()
    ManualControlService(servo).execute(active_session, ManualCommand.CENTER)
    assert servo.commands == [ManualCommand.CENTER]
```

- [ ] **Step 2: Run and verify RED**

Run: `pytest -q tests/unit/test_video_control.py`
Expected: FAIL because the control service does not exist.

- [ ] **Step 3: Implement bounded manual commands**

Implement the enum, exception, adapter protocol, and service. The service must reject commands when `control_available` is false and must invoke the adapter synchronously without a retry/queue mechanism.

- [ ] **Step 4: Run and verify GREEN**

Run: `pytest -q tests/unit/test_video_control.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/video/control.py app/video/adapters.py tests/unit/test_video_control.py
git commit -m "feat: add safe manual DRACO camera controls"
```

---

### Task 4: Snapshot and explicit recording lifecycle

**Files:**
- Create: `app/video/capture.py`
- Modify: `app/video/adapters.py`
- Test: `tests/unit/test_video_capture.py`

**Interfaces:**
- Produces: `CaptureMetadata`, `CaptureService.snapshot(session)`, `start_recording(session)`, `stop_recording(session)` and `CaptureAdapter`.

- [ ] **Step 1: Write failing capture tests**

```python
from app.video.capture import CaptureService

class FakeCapture:
    def __init__(self): self.recording = False
    def snapshot(self, metadata): return {"capture_id": "shot-1", "metadata": metadata}
    def start_recording(self, metadata): self.recording = True; return "rec-1"
    def stop_recording(self, recording_id): self.recording = False


def test_recording_is_off_until_explicit_start(active_session):
    adapter = FakeCapture()
    service = CaptureService(adapter)
    assert adapter.recording is False
    recording_id = service.start_recording(active_session)
    assert recording_id == "rec-1"
    assert adapter.recording is True


def test_snapshot_metadata_identifies_unit_and_operator(active_session):
    result = CaptureService(FakeCapture()).snapshot(active_session)
    assert result["metadata"].unit_id == active_session.unit_id
    assert result["metadata"].operator_id == active_session.operator_id
    assert result["metadata"].capture_type == "snapshot"
```

- [ ] **Step 2: Run and verify RED**

Run: `pytest -q tests/unit/test_video_capture.py`
Expected: FAIL because capture service does not exist.

- [ ] **Step 3: Implement capture metadata and service**

`CaptureMetadata` contains `unit_id`, `timestamp`, `operator_id`, `session_id`, and `capture_type`. Keep adapter errors local to capture calls; no capture method mutates session stream state.

- [ ] **Step 4: Run and verify GREEN**

Run: `pytest -q tests/unit/test_video_capture.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/video/capture.py app/video/adapters.py tests/unit/test_video_capture.py
git commit -m "feat: add DRACO snapshot and recording lifecycle"
```

---

### Task 5: Authenticated video API and auditing

**Files:**
- Create: `app/api/video.py`
- Modify: `app/main.py`
- Test: `tests/integration/test_video_api.py`

**Interfaces:**
- Consumes: existing `get_current_principal`, `require_roles`, `append_audit_event`, Tasks 1-4 services.
- Produces endpoints under `/api/draco/v1/video` for session creation, signaling, state, control, snapshot, recording start/stop, and session end.

- [ ] **Step 1: Write failing API tests**

```python
def test_unauthenticated_session_request_is_rejected(client):
    response = client.post("/api/draco/v1/video/sessions", json={"unit_id": "draco-mini-001"})
    assert response.status_code in (401, 403)


def test_authorized_operator_can_create_short_lived_session(operator_client):
    response = operator_client.post("/api/draco/v1/video/sessions", json={"unit_id": "draco-mini-001"})
    assert response.status_code == 201
    body = response.json()
    assert body["unit_id"] == "draco-mini-001"
    assert body["state"] == "CONNECTING"
    assert body["expires_at"]
```

Also assert audit records for `video.session.started`, `video.session.ended`, `video.snapshot.captured`, `video.recording.started`, `video.recording.stopped`, authorization/session expiry, and control-link failure/recovery using the repository's existing audit-test pattern.

- [ ] **Step 2: Run and verify RED**

Run: `pytest -q tests/integration/test_video_api.py`
Expected: FAIL because the video router is absent.

- [ ] **Step 3: Implement the router and include it in `app/main.py`**

Use `require_roles("draco_operator", "draco_admin")` for operator video actions. Every session-scoped endpoint must verify that the authenticated principal owns that session unless the principal is `draco_admin`. Return 404 for unknown session IDs, 409 for unavailable control, and 410 for expired sessions. Use `append_audit_event` for the specified events.

- [ ] **Step 4: Run API tests and the existing suite**

Run: `pytest -q tests/integration/test_video_api.py && pytest -q`
Expected: PASS with no existing-test regression.

- [ ] **Step 5: Commit**

```bash
git add app/api/video.py app/main.py tests/integration/test_video_api.py
git commit -m "feat: expose authenticated DRACO live video API"
```

---

### Task 6: Browser operator console

**Files:**
- Create: `app/static/draco_operator.html`
- Create: `app/static/draco_operator.js`
- Modify: `app/main.py`
- Test: `tests/unit/test_operator_console_contract.py`

**Interfaces:**
- Consumes: Task 5 `/api/draco/v1/video` API.
- Produces: `/operator/video` browser page with unit selection, video element, states, health/latency display, manual controls, snapshot/recording, fullscreen, and quality selection.

- [ ] **Step 1: Write failing console contract test**

```python
from pathlib import Path


def test_console_contains_required_live_video_controls():
    html = Path("app/static/draco_operator.html").read_text()
    for marker in [
        'id="live-video"', 'id="stream-state"', 'id="latency"',
        'data-command="PAN_LEFT"', 'data-command="PAN_RIGHT"',
        'data-command="TILT_UP"', 'data-command="TILT_DOWN"',
        'data-command="CENTER"', 'id="snapshot"', 'id="recording"',
        'id="quality"', 'id="fullscreen"'
    ]:
        assert marker in html


def test_console_has_link_lost_reconnect_behavior():
    js = Path("app/static/draco_operator.js").read_text()
    assert "LINK LOST — RECONNECTING" in js
    assert "RTCPeerConnection" in js
    assert "setControlsEnabled(false)" in js
```

- [ ] **Step 2: Run and verify RED**

Run: `pytest -q tests/unit/test_operator_console_contract.py`
Expected: FAIL because static console files do not exist.

- [ ] **Step 3: Implement the minimal console**

HTML must expose the markers above and a `<video id="live-video" autoplay playsinline></video>`. JavaScript must create `RTCPeerConnection`, POST an SDP offer to the authenticated session endpoint, install returned ICE configuration, attach the remote track to `live-video`, update ONLINE/CONNECTING/LIVE/DEGRADED/LINK LOST state, disable movement controls immediately on control/link loss, and use bounded exponential reconnect delays of 1, 2, 4, 8, then 10 seconds. Snapshot and recording actions call their explicit API endpoints. Do not auto-start recording.

Serve the page from FastAPI at `/operator/video`; retain the existing application and routers.

- [ ] **Step 4: Run console contract and full suite**

Run: `pytest -q tests/unit/test_operator_console_contract.py && pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/static app/main.py tests/unit/test_operator_console_contract.py
git commit -m "feat: add DRACO browser video console"
```

---

### Task 7: Pi capture/stream agent boundary and deployment contract

**Files:**
- Create: `device/draco_mini/video_agent.py`
- Create: `device/draco_mini/config.py`
- Create: `docs/draco-mini-video-agent.md`
- Test: `tests/unit/test_video_agent.py`

**Interfaces:**
- Produces: `VideoAgentConfig`, `VideoAgent.start()`, `heartbeat()`, and outbound-only signaling contract.
- Camera execution command is `rpicam-vid --width 1280 --height 720 --framerate 30 --codec h264 --inline` plus adapter-selected output transport.

- [ ] **Step 1: Write failing agent tests**

```python
from device.draco_mini.config import VideoAgentConfig
from device.draco_mini.video_agent import build_rpicam_command


def test_default_profile_is_720p30_h264():
    command = build_rpicam_command(VideoAgentConfig(unit_id="draco-mini-001", server_url="https://draco.example.test"))
    assert command[:2] == ["rpicam-vid", "--width"]
    assert "1280" in command
    assert "720" in command
    assert "30" in command
    assert "h264" in command


def test_agent_configuration_has_no_inbound_public_listener():
    config = VideoAgentConfig(unit_id="draco-mini-001", server_url="https://draco.example.test")
    assert not hasattr(config, "public_listen_port")
```

- [ ] **Step 2: Run and verify RED**

Run: `pytest -q tests/unit/test_video_agent.py`
Expected: FAIL because device video-agent modules do not exist.

- [ ] **Step 3: Implement the agent boundary**

Use a Pydantic settings model requiring `unit_id`, `server_url`, and a device credential supplied by environment/secret storage. `build_rpicam_command` must generate the exact 1280x720/30/H.264 baseline. Network methods initiate outbound HTTPS/WSS/WebRTC signaling only. Document installation of Raspberry Pi camera software and the system-service command without embedding credentials in repository files.

- [ ] **Step 4: Run agent and full tests**

Run: `pytest -q tests/unit/test_video_agent.py && pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add device/draco_mini docs/draco-mini-video-agent.md tests/unit/test_video_agent.py
git commit -m "feat: add DRACO-Mini outbound video agent"
```

---

### Task 8: End-to-end mocked acceptance and CI verification

**Files:**
- Create: `tests/integration/test_video_acceptance.py`
- Modify: existing GitHub Actions workflow only if the current workflow does not already execute `pytest -q` for all tests.

**Interfaces:**
- Consumes: all Tasks 1-7.
- Produces: deterministic CI evidence for the approved Gen-1 software acceptance path.

- [ ] **Step 1: Write failing acceptance test before any CI adjustment**

```python
def test_authorized_operator_video_lifecycle(operator_client, fake_video_runtime):
    created = operator_client.post("/api/draco/v1/video/sessions", json={"unit_id": "draco-mini-001"})
    assert created.status_code == 201
    session_id = created.json()["session_id"]

    offer = operator_client.post(
        f"/api/draco/v1/video/sessions/{session_id}/offer",
        json={"type": "offer", "sdp": "mock-offer"},
    )
    assert offer.status_code == 200
    assert offer.json()["answer"]["type"] == "answer"

    lost = operator_client.post(
        f"/api/draco/v1/video/sessions/{session_id}/state",
        json={"state": "LINK LOST"},
    )
    assert lost.status_code == 200

    blocked = operator_client.post(
        f"/api/draco/v1/video/sessions/{session_id}/control",
        json={"command": "PAN_LEFT"},
    )
    assert blocked.status_code == 409
```

Extend the same test module with recording-failure isolation and fresh-session reconnect assertions.

- [ ] **Step 2: Run acceptance test and verify RED if any contract is missing**

Run: `pytest -q tests/integration/test_video_acceptance.py`
Expected before final integration fixes: at least one assertion fails for any still-unwired contract; record the exact failure in the PR/commit notes.

- [ ] **Step 3: Make only the integration fixes required by the failing acceptance test**

Do not add new feature scope. Wire dependency overrides/fakes, state transitions, endpoint response shapes, or audit calls only where the RED evidence identifies a mismatch.

- [ ] **Step 4: Run fresh verification**

Run: `pytest -q`
Expected: all tests PASS. Then push the branch and inspect the GitHub Actions run for the exact head SHA; the required workflow job must complete successfully before claiming software acceptance.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_video_acceptance.py .github/workflows || true
git commit -m "test: verify DRACO live video acceptance path"
```

## Final Verification Gate

Before requesting merge, run and record fresh evidence for:

```bash
pytest -q
```

Then verify the GitHub Actions run attached to the exact PR head SHA is successful. Software acceptance means mocked/session/API/UI-contract tests pass; it does **not** prove physical Pi/camera capture, real TURN traversal, real servo motion, or measured field latency. Those remain hardware acceptance checks.
