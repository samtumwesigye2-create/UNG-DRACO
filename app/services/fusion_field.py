from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from math import sqrt
from threading import Lock
from uuid import uuid4
from app.services.math_analytics import vector_norm, sigma_residual

@dataclass
class FusionFieldEngine:
    lock: Lock = field(default_factory=Lock)
    observations: dict[str, dict] = field(default_factory=dict)
    history: list[dict] = field(default_factory=list)
    max_age_seconds: float = 5.0

    @staticmethod
    def _parse_time(value: str) -> datetime:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
        if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def ingest(self,sensor_id:str,position:list[float],confidence:float,quality:float=1.0,timestamp:str|None=None,metadata:dict|None=None)->dict:
        if sensor_id not in {"S1","S2","S3"}: raise ValueError("sensor_id must be S1, S2 or S3")
        if len(position) not in {2,3}: raise ValueError("position must contain 2 or 3 coordinates")
        pos=[float(v) for v in position]
        if len(pos)==2: pos.append(0.0)
        now=timestamp or datetime.now(timezone.utc).isoformat()
        self._parse_time(now)
        row={"observation_id":str(uuid4()),"sensor_id":sensor_id,"timestamp":now,"position":pos,
             "confidence":max(0.0,min(1.0,float(confidence))),"quality":max(0.0,min(1.0,float(quality))),
             "metadata":metadata or {}}
        with self.lock:
            self.observations[sensor_id]=row
            state=self._state()
            self.history.append(state)
            self.history=self.history[-300:]
            return state

    def _state(self)->dict:
        now=datetime.now(timezone.utc)
        all_rows=list(self.observations.values())
        rows=[]; stale=[]
        for r in all_rows:
            age=max(0.0,(now-self._parse_time(r["timestamp"])).total_seconds())
            if age <= self.max_age_seconds: rows.append({**r,"age_seconds":round(age,3),"stale":False})
            else: stale.append(r["sensor_id"])
        if not rows:
            return {"status":"waiting","sensors":{},"focus":None,"confidence":0.0,"envelope_radius":None,
                    "residuals":{},"anomaly":False,"stale_sensors":stale}
        weights=[max(.001,r["confidence"]*r["quality"]) for r in rows]
        total=sum(weights)
        focus=[sum(r["position"][i]*w for r,w in zip(rows,weights))/total for i in range(3)]
        distances={r["sensor_id"]:vector_norm([r["position"][i]-focus[i] for i in range(3)]) for r in rows}
        radius=sqrt(sum(w*distances[r["sensor_id"]]**2 for r,w in zip(rows,weights))/total)
        # Robust cross-sensor disagreement: compare each residual with median residual, while preserving
        # a minimum physical scale so near-identical observations do not amplify floating-point noise.
        vals=sorted(distances.values()); median=vals[len(vals)//2]
        scale=max(1.0,median)
        normalized={k:v/scale for k,v in distances.items()}
        residual_values=list(distances.values())
        residual_mean=sum(residual_values)/len(residual_values)
        residual_std=sqrt(sum((v-residual_mean)**2 for v in residual_values)/len(residual_values)) if len(residual_values)>1 else 0.0
        sigma={k:sigma_residual(v,residual_mean,residual_std) for k,v in distances.items()}
        anomaly=any(v>2.5 for v in normalized.values()) if len(rows)>=2 else False
        return {"state_id":str(uuid4()),"timestamp":now.isoformat(),"status":"fused" if len(rows)>=2 else "partial",
                "sensors":{r["sensor_id"]:{**r,"weight":w/total} for r,w in zip(rows,weights)},
                "focus":focus,"confidence":round(sum(weights)/len(weights),4),"envelope_radius":round(radius,4),
                "residuals":distances,"normalized_residuals":normalized,"sigma_residuals":sigma,"anomaly":anomaly,
                "stale_sensors":stale,"provenance":[r["observation_id"] for r in rows]}

    def state(self)->dict:
        with self.lock: return self._state()
    def replay(self,limit:int=100)->list[dict]:
        with self.lock: return self.history[-max(1,min(limit,300)):]

fusion_field=FusionFieldEngine()
