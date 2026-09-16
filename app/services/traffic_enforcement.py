"""Traffic-scene enrichment for DRACO observations.

This module ports the useful, non-UI concepts from the traffic-enforcement
handoff into DRACO's existing FastAPI/service architecture.  It deliberately
keeps enforcement decisions human-reviewed: detections are evidence/flags,
not automatic legal conclusions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import atan2, degrees, hypot
from typing import Iterable


@dataclass(frozen=True)
class TrafficObservation:
    plate_text: str | None = None
    plate_confidence: float = 0.0
    speed_kmh: float | None = None
    direction_deg: float | None = None
    direction_label: str | None = None
    detection_flags: tuple[str, ...] = ()
    review_required: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_plate(value: str | None) -> str | None:
    if not value:
        return None
    normalized = "".join(ch for ch in value.upper() if ch.isalnum())
    return normalized or None


def direction_from_motion(dx: float, dy: float) -> tuple[float, str]:
    """Return compass-style heading and an 8-point label from image motion."""
    angle = (degrees(atan2(dx, -dy)) + 360.0) % 360.0
    labels = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    label = labels[int((angle + 22.5) // 45.0) % 8]
    return round(angle, 1), label


def estimate_speed_kmh(dx_px: float, dy_px: float, elapsed_s: float, pixels_per_meter: float) -> float | None:
    """Estimate scene-plane speed when the camera has been calibrated."""
    if elapsed_s <= 0 or pixels_per_meter <= 0:
        return None
    meters = hypot(dx_px, dy_px) / pixels_per_meter
    return round((meters / elapsed_s) * 3.6, 1)


def build_traffic_observation(
    *,
    plate_text: str | None = None,
    plate_confidence: float = 0.0,
    speed_kmh: float | None = None,
    direction_deg: float | None = None,
    direction_label: str | None = None,
    detector_flags: Iterable[str] = (),
    configured_speed_threshold_kmh: float | None = None,
) -> TrafficObservation:
    """Normalize detector output into a DRACO-friendly observation payload.

    Speed flags require an explicitly configured/calibrated threshold.  The
    resulting flags always require operator review before any downstream
    notification or enforcement workflow.
    """
    flags = {str(flag).strip().upper() for flag in detector_flags if str(flag).strip()}
    if (
        configured_speed_threshold_kmh is not None
        and speed_kmh is not None
        and speed_kmh >= configured_speed_threshold_kmh
    ):
        flags.add("SPEED_THRESHOLD_EXCEEDED")
    return TrafficObservation(
        plate_text=normalize_plate(plate_text),
        plate_confidence=max(0.0, min(float(plate_confidence), 1.0)),
        speed_kmh=speed_kmh,
        direction_deg=direction_deg,
        direction_label=direction_label,
        detection_flags=tuple(sorted(flags)),
        review_required=True,
    )
