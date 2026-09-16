# DRACO Gen-1 Live Operator Video Design

**Date:** 2026-09-16
**Status:** Approved design

## Goal

Add secure, low-latency live video from DRACO-Mini to an authenticated browser-based DRACO operator console, with manual pan/tilt, snapshots, operator-controlled recording, stream health, and safe reconnect behavior.

## Scope

Gen-1 is a live observation and manual camera-operation subsystem. It does not include autonomous tracking, targeting, weapon control, firing, laser designation, or autonomous engagement.

## Architecture

DRACO-Mini uses a Raspberry Pi Zero 2 W and Camera Module 3 NoIR. The Pi captures and encodes video and establishes outbound connections only; it does not expose a public camera port. The DRACO service provides authenticated signaling/session coordination and supports a TURN relay when NAT or firewall traversal prevents a direct WebRTC path. An authenticated operator opens the existing DRACO web application in a browser and selects a registered unit to establish a short-lived live-view session.

Primary path:

`Camera Module 3 NoIR -> Pi Zero 2 W -> outbound encrypted WebRTC/signaling connection -> DRACO signaling/TURN boundary -> authenticated DRACO web console -> operator`

Video and camera-control traffic use separate logical channels. Congestion or interruption of video must not queue stale pan/tilt commands.

## Video Session

The default Gen-1 operating profile is 720p at 30 frames per second, optimized for low latency rather than maximum resolution. Operators may select lower stream quality/bitrate when network conditions require it.

A viewing session is short-lived and tied to the authenticated DRACO principal and a specific DRACO-Mini unit. Authorization expiry terminates viewing and requires a new authorized session. The browser automatically attempts to negotiate a fresh session after recoverable network interruption.

The operator-facing stream states are:

- ONLINE
- CONNECTING
- LIVE
- DEGRADED
- LINK LOST

When connectivity is lost, the console displays `LINK LOST — RECONNECTING` and immediately disables camera movement commands until the authenticated control channel is restored.

## Operator Console

The Gen-1 operator console is browser-based and integrated into DRACO rather than implemented as a separate desktop application. A unit view contains the 720p/30 live feed plus unobtrusive stream status, connection quality/latency, and unit online/offline state.

Authorized controls are:

- pan left/right
- tilt up/down
- center/home
- snapshot
- start/stop recording
- fullscreen
- stream quality/bitrate selection

Recording is off by default and starts only after an explicit authorized operator action.

## Remote Internet Access and Security

Remote viewing over the internet is supported. DRACO-Mini initiates outbound encrypted connections and is not directly exposed as an internet-facing camera service. WebRTC encrypted media transport carries live video; TURN is available as a relay fallback when a direct peer path is unavailable.

The existing DRACO authentication/RBAC boundary authorizes operator access. Viewing sessions are short-lived. Expired or revoked authorization terminates the session. The design extends the existing DRACO audit mechanism rather than creating a second security/audit subsystem.

## Recording, Snapshots, and Metadata

Live viewing and recording are independent. A recording failure must not terminate an otherwise healthy live stream. Snapshots and operator-requested recordings carry:

- DRACO unit ID
- timestamp
- operator/session ID
- capture type

Recording storage implementation must remain behind a focused storage interface so storage policy can evolve without changing the live-stream/session API.

## Audit Events

DRACO records security-relevant operator actions using its existing audit facility. At minimum the subsystem emits events for session requested/started/ended, authorization denial or expiry, snapshot capture, recording start/stop/failure, and material control-channel failure/recovery.

## Failure Behavior

A lost internet connection stops remote viewing safely; it never redirects or exposes the camera stream. The unit re-establishes its outbound authenticated connection when connectivity returns. Lost control connectivity disables pan/tilt immediately. Failed recording does not interrupt live video. The UI clearly reports degraded or lost links rather than silently presenting stale video as live.

## Component Boundaries

1. **Pi capture/stream agent:** camera capture, H.264 profile, outbound signaling, WebRTC media, unit heartbeat, and a bounded manual pan/tilt command adapter.
2. **DRACO session/signaling service:** authenticated short-lived session creation, unit/session association, signaling exchange, session expiry, and relay configuration.
3. **DRACO control service:** validates authorized manual camera commands and rejects commands when the control session is unavailable or expired.
4. **Capture/recording service:** explicit snapshot/record lifecycle and metadata; isolated from live viewing.
5. **Operator web console:** unit selection, WebRTC negotiation, live video, status indicators, manual controls, recording/snapshot actions, reconnect state.
6. **Audit integration:** records operator/session/security events through the existing DRACO audit mechanism.

## Testing and Acceptance

CI must not require physical Pi or camera hardware. Tests use mocked camera/WebRTC/signaling/control adapters and cover:

- authorized session creation
- unauthorized stream rejection
- session expiration
- reconnect negotiation
- control commands disabled after control-channel loss
- snapshot behavior
- recording start/stop and recording failure isolation
- audit events for session and capture actions
- WebRTC signaling contract behavior
- stream state transitions including degraded and link-lost conditions

Hardware acceptance is separate from CI and will validate Camera Module 3 NoIR capture, Pi Zero 2 W performance at the 720p/30 target, real network traversal, pan/tilt hardware operation, and end-to-end latency.

## Non-Goals

Gen-1 does not add autonomous tracking, object targeting, weapon interfaces, firing controls, laser designation, or autonomous engagement. It also does not require a dedicated desktop operator application or a public inbound port on DRACO-Mini.
