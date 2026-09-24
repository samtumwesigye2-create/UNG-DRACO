from __future__ import annotations

import asyncio
from pathlib import Path
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.services.fusion_field import fusion_field
from app.services.fusion_sensor_adapter import ingest_measurement

router = APIRouter(tags=["fusion field"])
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"

class SensorObservation(BaseModel):
    sensor_id: str
    position: list[float] = Field(min_length=2, max_length=3)
    confidence: float = Field(default=.5, ge=0, le=1)
    quality: float = Field(default=1.0, ge=0, le=1)
    timestamp: str | None = None
    metadata: dict | None = None

@router.get("/fusion-field", include_in_schema=False)
def fusion_field_ui() -> FileResponse:
    return FileResponse(STATIC_DIR / "draco_fusion_field.html")

@router.post("/api/draco/v1/fusion-field/observations")
def ingest_observation(body: SensorObservation) -> dict:
    try:
        return ingest_measurement(**body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@router.get("/api/draco/v1/fusion-field/state")
def state() -> dict:
    return fusion_field.state()

@router.get("/api/draco/v1/fusion-field/replay")
def replay(limit: int = 100) -> dict:
    return {"states": fusion_field.replay(limit)}

@router.websocket("/api/draco/v1/fusion-field/stream")
async def stream(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        last_state_id=None
        while True:
            current=fusion_field.state()
            state_id=current.get("state_id")
            if state_id != last_state_id:
                await websocket.send_json(current)
                last_state_id=state_id
            await asyncio.sleep(.1)
    except WebSocketDisconnect:
        return
