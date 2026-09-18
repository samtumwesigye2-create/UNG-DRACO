from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from threading import Lock

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/draco/v1/device", tags=["device link"])

_LOCK = Lock()
_UNITS: dict[str, dict] = {}
STALE_AFTER = timedelta(seconds=max(15, int(os.getenv("DRACO_UNIT_STALE_SECONDS", "45"))))


class Heartbeat(BaseModel):
    unit_id: str = Field(min_length=1, max_length=128)
    software_version: str | None = Field(default=None, max_length=64)
    rgb_noir: str = Field(default="unknown", max_length=32)
    thermal: str = Field(default="unknown", max_length=32)
    motion_controller: str = Field(default="unknown", max_length=32)
    signaling: bool = False
    capture: bool = False
    camera_control: bool = False
    cpu_temperature_c: float | None = None
    uptime_seconds: int | None = Field(default=None, ge=0)


def _authorize(token: str | None) -> None:
    expected = os.getenv("DRACO_UNIT_TOKEN", "")
    if not expected:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "DRACO unit authentication is not configured")
    if token != expected:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid DRACO unit token")


@router.post("/heartbeat")
def heartbeat(payload: Heartbeat, x_draco_unit_token: str | None = Header(default=None)) -> dict:
    _authorize(x_draco_unit_token)
    now = datetime.now(timezone.utc)
    row = {
        **payload.model_dump(),
        "last_seen": now.isoformat(),
        "_last_seen_dt": now,
    }
    with _LOCK:
        _UNITS[payload.unit_id] = row
    public = {k: v for k, v in row.items() if not k.startswith("_")}
    return {"accepted": True, "unit": public}


@router.get("/units")
def units() -> dict:
    now = datetime.now(timezone.utc)
    output = []
    with _LOCK:
        for row in _UNITS.values():
            item = {k: v for k, v in row.items() if not k.startswith("_")}
            item["online"] = now - row["_last_seen_dt"] <= STALE_AFTER
            output.append(item)
    output.sort(key=lambda x: x["unit_id"])
    return {"units": output, "stale_after_seconds": int(STALE_AFTER.total_seconds())}


def latest_unit() -> dict | None:
    now = datetime.now(timezone.utc)
    with _LOCK:
        if not _UNITS:
            return None
        row = max(_UNITS.values(), key=lambda x: x["_last_seen_dt"])
        item = {k: v for k, v in row.items() if not k.startswith("_")}
        item["online"] = now - row["_last_seen_dt"] <= STALE_AFTER
        return item
