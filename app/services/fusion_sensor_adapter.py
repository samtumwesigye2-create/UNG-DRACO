from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from app.services.fusion_field import fusion_field

SENSOR_SLOTS={"S1","S2","S3"}

@dataclass(frozen=True)
class NormalizedSensorMeasurement:
    sensor_id:str
    position:list[float]
    confidence:float
    quality:float
    timestamp:str
    metadata:dict

def normalize_measurement(sensor_id:str,position:list[float],confidence:float,quality:float=1.0,timestamp:str|None=None,metadata:dict|None=None)->NormalizedSensorMeasurement:
    if sensor_id not in SENSOR_SLOTS: raise ValueError("sensor_id must be S1, S2 or S3")
    if len(position) not in {2,3}: raise ValueError("position must contain 2 or 3 coordinates")
    coords=[float(v) for v in position]
    if not all(isfinite(v) for v in coords): raise ValueError("position coordinates must be finite")
    if len(coords)==2: coords.append(0.0)
    stamp=timestamp or datetime.now(timezone.utc).isoformat()
    try: datetime.fromisoformat(stamp.replace("Z","+00:00"))
    except ValueError as exc: raise ValueError("timestamp must be ISO-8601") from exc
    return NormalizedSensorMeasurement(sensor_id,coords,max(0.0,min(1.0,float(confidence))),max(0.0,min(1.0,float(quality))),stamp,dict(metadata or {}))

def ingest_measurement(**kwargs)->dict:
    m=normalize_measurement(**kwargs)
    return fusion_field.ingest(sensor_id=m.sensor_id,position=m.position,confidence=m.confidence,quality=m.quality,timestamp=m.timestamp,metadata=m.metadata)
