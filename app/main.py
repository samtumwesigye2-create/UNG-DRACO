from app.frame_propagation import register_frame, convert_position, link_timing
from pathlib import Path
import os
import urllib.error
import urllib.request
import shutil
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.operations import router as operations_router
from app.api.device import router as device_router, latest_unit
from app.api.traffic import router as traffic_router
from app.api.video import router as video_router
from app.database import database_ready, get_db
from app.models import CollectionItem, Source, Watch
from app.security.audit import append_audit_event
from app.security.auth import get_current_principal
from app.security.rbac import Principal, require_roles
from app.services.alerts import evaluate_watches
from app.services.correlation import correlate_observations
from app.services.fusion import build_assessment
from app.services.nexus_transport import build_observation_event, relay_event
from app.services.tracking import upsert_track

STATIC_DIR = Path(__file__).resolve().parent / "static"
app = FastAPI(title="UNG-DRACO", version="1.1.0")
app.include_router(operations_router)
app.include_router(device_router)
app.include_router(video_router)
app.include_router(traffic_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.on_event("startup")
def run_transport_acceptance_once() -> None:
    if os.getenv("DRACO_ACCEPTANCE_ONCE","").lower() not in {"1","true","yes"}:
        return
    event_id=os.getenv("DRACO_ACCEPTANCE_EVENT_ID") or str(uuid4())
    envelope={
        "source_system":"UNG-DRACO",
        "target_system":"UNG-PULSAR",
        "message_type":"observation.created",
        "message_id":event_id,
        "correlation_id":event_id,
        "trace_id":event_id,
        "schema_version":"1.0",
        "priority":10,
        "classification":"internal",
        "payload":{
            "event_id":event_id,
            "device_id":"DRACO-ACCEPTANCE",
            "sensor_id":"synthetic",
            "timestamp":"startup",
            "sensor_type":"synthetic",
            "domain":"acceptance-test",
            "location":None,
            "confidence":1.0,
            "observation_id":event_id,
            "synthetic":True,
        },
    }
    result=relay_event(envelope)
    print(f"DRACO_ACCEPTANCE event_id={event_id} result={result}",flush=True)


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse: return FileResponse(STATIC_DIR / "draco_dashboard.html")

@app.get("/operator/video", include_in_schema=False)
def operator_video() -> FileResponse: return FileResponse(STATIC_DIR / "draco_operator.html")

@app.get("/operator/traffic", include_in_schema=False)
def operator_traffic() -> FileResponse: return FileResponse(STATIC_DIR / "draco_traffic.html")

class ObservationCreate(BaseModel):
    source_type: str = Field(min_length=1, max_length=64)
    domain: str = Field(min_length=1, max_length=32)
    platform: str | None = Field(default=None, max_length=128)
    location: dict | None = None
    raw_content: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
class SourceCreate(BaseModel):
    real_name: str = Field(min_length=1, max_length=255); contact: str | None = None; notes: str | None = None
class WatchCreate(BaseModel):
    target: str = Field(min_length=1, max_length=255); target_type: str = Field(min_length=1, max_length=64)
@app.get("/health")
def health() -> dict[str,str]: return {"system":"UNG-DRACO","status":"ok"}
@app.get("/ready")
def ready(response:Response)->dict[str,str]:
    if database_ready(): return {"system":"UNG-DRACO","status":"ready"}
    response.status_code=status.HTTP_503_SERVICE_UNAVAILABLE; return {"system":"UNG-DRACO","status":"not_ready"}
@app.get("/v1/integration/health")
def integration_health() -> dict:
    nexus=os.getenv("NEXUS_BASE_URL","").rstrip("/")
    if not nexus:
        return {"nexus":"not_configured","live_link":False}
    try:
        req=urllib.request.Request(nexus+"/health",headers={"User-Agent":"UNG-DRACO/1.1.0"})
        with urllib.request.urlopen(req,timeout=3) as response:
            ok=200 <= int(response.status) < 300
        return {"nexus":"online" if ok else "degraded","live_link":ok}
    except Exception:
        return {"nexus":"offline","live_link":False}

def _read_first(path: str) -> str | None:
    try:
        return Path(path).read_text().strip()
    except Exception:
        return None


def _memory_metrics() -> dict:
    values={}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            key,val=line.split(":",1); values[key]=int(val.strip().split()[0])*1024
    except Exception:
        return {"total_bytes":None,"available_bytes":None,"used_percent":None}
    total=values.get("MemTotal"); available=values.get("MemAvailable")
    used_percent=round((1-(available/total))*100,1) if total and available is not None else None
    return {"total_bytes":total,"available_bytes":available,"used_percent":used_percent}


def _cpu_temp_c() -> float | None:
    for path in ("/sys/class/thermal/thermal_zone0/temp","/sys/devices/virtual/thermal/thermal_zone0/temp"):
        raw=_read_first(path)
        if raw:
            try:
                value=float(raw); return round(value/1000 if value>1000 else value,1)
            except ValueError:
                pass
    return None


@app.get("/v1/device/health")
def device_health() -> dict:
    disk=shutil.disk_usage("/")
    uptime_raw=_read_first("/proc/uptime")
    uptime_seconds=int(float(uptime_raw.split()[0])) if uptime_raw else None
    try: load1,load5,load15=os.getloadavg()
    except Exception: load1=load5=load15=None
    return {
        "service":"UNG-DRACO",
        "runtime":os.getenv("RAILWAY_ENVIRONMENT_NAME") or os.getenv("ENVIRONMENT","unknown"),
        "uptime_seconds":uptime_seconds,
        "cpu":{"load_1m":round(load1,2) if load1 is not None else None,"load_5m":round(load5,2) if load5 is not None else None,"load_15m":round(load15,2) if load15 is not None else None,"temperature_c":_cpu_temp_c()},
        "memory":_memory_metrics(),
        "storage":{"total_bytes":disk.total,"free_bytes":disk.free,"used_percent":round((disk.used/disk.total)*100,1) if disk.total else None},
        "hardware":((lambda u: {"rgb_noir":u.get("rgb_noir"),"thermal":u.get("thermal"),"motion_controller":u.get("motion_controller"),"unit_id":u.get("unit_id"),"online":u.get("online"),"last_seen":u.get("last_seen")} if u else {"rgb_noir":"not_connected","thermal":"not_connected","motion_controller":"not_connected","unit_id":None,"online":False,"last_seen":None})(latest_unit())),
    }

@app.get("/v1/security/probe")
def security_probe(principal:Principal=Depends(get_current_principal))->dict[str,str]: return {"subject":principal.subject,"status":"authenticated"}
@app.post("/api/draco/v1/observations",status_code=status.HTTP_201_CREATED)
def create_observation(payload:ObservationCreate,db:Session=Depends(get_db),principal:Principal=Depends(require_roles("draco_collector","draco_admin")))->dict[str,str]:
    observation=CollectionItem(source_type=payload.source_type,domain=payload.domain,platform=payload.platform,location=payload.location,raw_content=payload.raw_content,confidence=payload.confidence)
    try:
        db.add(observation);db.flush();append_audit_event(db,actor_id=principal.subject,action="observation.created",resource_type="collection_item",resource_id=str(observation.id),correlation_id=str(uuid4()),result="success",request_metadata={"source_type":payload.source_type,"domain":payload.domain,"event":"draco.observation.created"});db.commit()
    except Exception: db.rollback();raise
    envelope=build_observation_event(observation_id=str(observation.id),source_type=payload.source_type,domain=payload.domain,platform=payload.platform,location=payload.location,confidence=payload.confidence)
    relay=relay_event(envelope)
    return {"status":"accepted","observation_id":str(observation.id),"event":"draco.observation.created","event_id":envelope["message_id"],"nexus":relay}
@app.post("/api/draco/v1/observations/{observation_id}/process")
def process_observation(observation_id:str,db:Session=Depends(get_db),principal:Principal=Depends(require_roles("draco_analyst","draco_admin")))->dict:
    observation=db.get(CollectionItem,observation_id)
    if observation is None: raise HTTPException(status_code=404,detail="observation not found")
    correlation_id=str(uuid4())
    try:
        related=correlate_observations(db,observation.id);track=upsert_track(db,observation,related);product=build_assessment(db,track);alerts=evaluate_watches(db,track);append_audit_event(db,actor_id=principal.subject,action="track.processed",resource_type="track",resource_id=str(track.id),correlation_id=correlation_id,result="success",request_metadata={"observation_id":str(observation.id),"related_observation_ids":[str(i.id) for i in related]});append_audit_event(db,actor_id=principal.subject,action="intelligence_product.created",resource_type="intelligence_product",resource_id=str(product.id),correlation_id=correlation_id,result="success",request_metadata={"track_id":str(track.id)})
        for alert in alerts: append_audit_event(db,actor_id=principal.subject,action="alert.created",resource_type="alert",resource_id=str(alert.id),correlation_id=correlation_id,result="success",request_metadata={"track_id":str(track.id),"watch_id":str(alert.watch_id)})
        db.commit()
    except Exception: db.rollback();raise
    return {"status":"processed","observation_id":str(observation.id),"correlated_observation_ids":[str(i.id) for i in related],"track_id":str(track.id),"track_status":track.status,"product_id":str(product.id),"alert_ids":[str(a.id) for a in alerts],"correlation_id":correlation_id}
@app.post("/api/draco/v1/sources",status_code=201)
def create_source(payload:SourceCreate,db:Session=Depends(get_db),principal:Principal=Depends(require_roles("draco_source_admin","draco_admin")))->dict[str,str]:
    source=Source(real_name=payload.real_name,contact=payload.contact,notes=payload.notes)
    try: db.add(source);db.flush();append_audit_event(db,actor_id=principal.subject,action="source.registered",resource_type="source",resource_id=str(source.id),correlation_id=str(uuid4()),result="success",request_metadata={"real_name":payload.real_name});db.commit()
    except Exception: db.rollback();raise
    return {"status":"registered","source_id":str(source.id)}
@app.get("/api/draco/v1/sources")
def list_sources(db:Session=Depends(get_db),principal:Principal=Depends(require_roles("draco_source_admin","draco_admin")))->list[dict]: return [{"id":str(i.id),"real_name":i.real_name,"contact":i.contact,"notes":i.notes} for i in db.scalars(select(Source).order_by(Source.created_at.asc())).all()]
@app.post("/api/draco/v1/watches",status_code=201)
def create_watch(payload:WatchCreate,db:Session=Depends(get_db),principal:Principal=Depends(require_roles("draco_analyst","draco_admin")))->dict:
    watch=Watch(target=payload.target,target_type=payload.target_type,active=True)
    try: db.add(watch);db.flush();append_audit_event(db,actor_id=principal.subject,action="watch.created",resource_type="watch",resource_id=str(watch.id),correlation_id=str(uuid4()),result="success",request_metadata={"target":payload.target,"target_type":payload.target_type});db.commit()
    except Exception: db.rollback();raise
    return {"watch_id":str(watch.id),"active":watch.active}
@app.get("/api/draco/v1/watches")
def list_watches(db:Session=Depends(get_db),principal:Principal=Depends(require_roles("draco_analyst","draco_admin")))->list[dict]:
    rows=db.scalars(select(Watch).order_by(Watch.created_at.asc())).all();return [{"id":str(i.id),"target":i.target,"target_type":i.target_type,"active":i.active,"start_date":i.start_date.isoformat() if i.start_date else None,"end_date":i.end_date.isoformat() if i.end_date else None} for i in rows]

@app.post("/v1/frames/register")
def ung_frame_register(body: dict):
    return register_frame(body["source"],body["destination"],body["matrix"],body.get("timestamp"),body.get("version","ung-frame-v1"))
@app.post("/v1/frames/convert")
def ung_frame_convert(body: dict):
    return convert_position(body["position"],body["source"],body["destination"])
@app.post("/v1/propagation/link")
def ung_propagation_link(body: dict):
    return link_timing(body["origin_m"],body["destination_m"],float(body.get("speed_mps",299792458.0)))
