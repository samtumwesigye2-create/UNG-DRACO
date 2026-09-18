#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import platform
import time
import urllib.error
import urllib.request
from pathlib import Path

CLOUD_BASE_URL=os.getenv("DRACO_CLOUD_BASE_URL","https://ung-draco-production-f6b7.up.railway.app").rstrip("/")
UNIT_ID=os.getenv("DRACO_UNIT_ID","draco-mini-001")
UNIT_TOKEN=os.getenv("DRACO_UNIT_TOKEN","")
INTERVAL=max(10,int(os.getenv("DRACO_HEARTBEAT_INTERVAL","20")))


def read_first(path:str):
    try:return Path(path).read_text().strip()
    except Exception:return None


def cpu_temp_c():
    raw=read_first("/sys/class/thermal/thermal_zone0/temp")
    if not raw:return None
    try:
        v=float(raw);return round(v/1000 if v>1000 else v,1)
    except ValueError:return None


def uptime_seconds():
    raw=read_first("/proc/uptime")
    if not raw:return None
    try:return int(float(raw.split()[0]))
    except Exception:return None


def detect_camera():
    for p in ("/dev/video0","/dev/video1"):
        if Path(p).exists():return "connected"
    return "not_connected"


def detect_motion():
    for p in ("/dev/ttyACM0","/dev/ttyUSB0"):
        if Path(p).exists():return "connected"
    return "not_connected"


def payload():
    return {
        "unit_id":UNIT_ID,
        "software_version":"gen1-link-1.0",
        "rgb_noir":detect_camera(),
        "thermal":os.getenv("DRACO_THERMAL_STATUS","not_connected"),
        "motion_controller":detect_motion(),
        "signaling":os.getenv("DRACO_SIGNALING_READY","false").lower() in {"1","true","yes"},
        "capture":detect_camera()=="connected",
        "camera_control":detect_motion()=="connected",
        "cpu_temperature_c":cpu_temp_c(),
        "uptime_seconds":uptime_seconds(),
    }


def send():
    if not UNIT_TOKEN:
        raise RuntimeError("DRACO_UNIT_TOKEN is required")
    body=json.dumps(payload(),separators=(",",":")).encode()
    req=urllib.request.Request(
        CLOUD_BASE_URL+"/api/draco/v1/device/heartbeat",
        data=body,
        method="POST",
        headers={
            "Content-Type":"application/json",
            "X-DRACO-Unit-Token":UNIT_TOKEN,
            "User-Agent":f"UNG-DRACO-Unit/{platform.node() or UNIT_ID}",
        },
    )
    with urllib.request.urlopen(req,timeout=8) as response:
        return int(response.status)


def main():
    while True:
        try:
            code=send()
            print(f"heartbeat unit={UNIT_ID} status={code}",flush=True)
        except Exception as exc:
            print(f"heartbeat unit={UNIT_ID} error={type(exc).__name__}",flush=True)
        time.sleep(INTERVAL)


if __name__=="__main__":
    main()
