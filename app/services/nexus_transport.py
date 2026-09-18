from __future__ import annotations
import os
from datetime import datetime, timezone
from uuid import uuid4
import httpx

NEXUS_BASE_URL=os.getenv("NEXUS_BASE_URL","").rstrip("/")
NEXUS_SERVICE_TOKEN=os.getenv("NEXUS_SERVICE_TOKEN","")
NEXUS_TIMEOUT=float(os.getenv("NEXUS_TIMEOUT","8"))

def build_observation_event(*,observation_id:str,source_type:str,domain:str,platform:str|None,location:dict|None,confidence:float)->dict:
    event_id=str(uuid4())
    return {
        "source_system":"UNG-DRACO",
        "target_system":"UNG-PULSAR",
        "message_type":"observation.created",
        "message_id":event_id,
        "correlation_id":observation_id,
        "trace_id":event_id,
        "schema_version":"1.0",
        "priority":50,
        "classification":"internal",
        "payload":{
            "event_id":event_id,
            "device_id":platform or "UNG-DRACO",
            "sensor_id":source_type,
            "timestamp":datetime.now(timezone.utc).isoformat(),
            "sensor_type":source_type,
            "domain":domain,
            "location":location,
            "confidence":confidence,
            "observation_id":observation_id,
        },
    }

def relay_event(envelope:dict)->dict:
    if not NEXUS_BASE_URL:return {"relayed":False,"reason":"nexus_not_configured"}
    headers={"Content-Type":"application/json"}
    if NEXUS_SERVICE_TOKEN:headers["Authorization"]=f"Bearer {NEXUS_SERVICE_TOKEN}"
    try:
        with httpx.Client(timeout=NEXUS_TIMEOUT) as client:
            response=client.post(f"{NEXUS_BASE_URL}/v1/messages",json=envelope,headers=headers)
        return {"relayed":response.is_success,"status_code":response.status_code,"response":response.json() if response.content else None}
    except Exception as exc:
        return {"relayed":False,"reason":type(exc).__name__}
