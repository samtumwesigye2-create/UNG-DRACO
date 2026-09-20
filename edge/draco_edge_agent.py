#!/usr/bin/env python3
"""UNG-DRACO Gen-1 Raspberry Pi edge agent.

Sends authenticated unit health to the DRACO cloud service. Sensor checks are
local-only and fail closed to "not_connected" when hardware is absent.
"""
import json, os, socket, time, urllib.request
from pathlib import Path

BASE=os.getenv("DRACO_BASE_URL","https://ung-draco-production-9552.up.railway.app").rstrip("/")
TOKEN=os.getenv("DRACO_UNIT_TOKEN","")
UNIT=os.getenv("DRACO_UNIT_ID",socket.gethostname() or "DRACO-GEN1")
INTERVAL=max(10,int(os.getenv("DRACO_HEARTBEAT_SECONDS","20")))

def exists_any(paths):
    return any(Path(p).exists() for p in paths)

def cpu_temp():
    try: return round(float(Path("/sys/class/thermal/thermal_zone0/temp").read_text())/1000,1)
    except Exception: return None

def uptime():
    try: return int(float(Path("/proc/uptime").read_text().split()[0]))
    except Exception: return None

def camera_state():
    return "connected" if exists_any(["/dev/video0","/dev/media0"]) else "not_connected"

def thermal_state():
    # Set DRACO_THERMAL_DEVICE to the concrete device path once the module is installed.
    p=os.getenv("DRACO_THERMAL_DEVICE","")
    return "connected" if p and Path(p).exists() else "not_connected"

def motion_state():
    # Set DRACO_MOTION_DEVICE (for example /dev/ttyUSB0) when the controller is installed.
    p=os.getenv("DRACO_MOTION_DEVICE","")
    return "connected" if p and Path(p).exists() else "not_connected"

def heartbeat():
    body=json.dumps({
      "unit_id":UNIT,"software_version":"gen1-edge-1.0",
      "rgb_noir":camera_state(),"thermal":thermal_state(),
      "motion_controller":motion_state(),"signaling":True,
      "capture":camera_state()=="connected","camera_control":motion_state()=="connected",
      "cpu_temperature_c":cpu_temp(),"uptime_seconds":uptime()
    }).encode()
    req=urllib.request.Request(BASE+"/api/draco/v1/device/heartbeat",data=body,
      headers={"Content-Type":"application/json","X-DRACO-Unit-Token":TOKEN},method="POST")
    with urllib.request.urlopen(req,timeout=8) as r: return r.status

if __name__=="__main__":
    if not TOKEN: raise SystemExit("DRACO_UNIT_TOKEN is required")
    while True:
        try: print("heartbeat",heartbeat(),flush=True)
        except Exception as e: print("heartbeat_error",repr(e),flush=True)
        time.sleep(INTERVAL)
