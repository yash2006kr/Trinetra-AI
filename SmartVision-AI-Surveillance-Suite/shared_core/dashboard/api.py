"""Dashboard REST and WebSocket routes."""

from __future__ import annotations

import asyncio
import base64
import json
import shutil
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import cv2
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from shared_core.alert_engine.alerts import Alert, AlertPriority
from shared_core.dashboard.auth import require_api_key
from shared_core.database.repository import EventRepository
from shared_core.stream_manager.camera_manager import CameraManager
from shared_core.utils.config import load_config


def create_dashboard_router(camera_manager: CameraManager | None = None, repository: EventRepository | None = None) -> APIRouter:
    config = load_config()
    repo = repository or EventRepository.from_config(config)
    manager = camera_manager or CameraManager()
    router = APIRouter(prefix="/api", tags=["dashboard"])

    @router.get("/health")
    def health() -> dict[str, Any]:
        runtime = config.get("ai", {})
        return {"status": "ok", "service": "smartvision-api", "ai": runtime}

    @router.get("/events", dependencies=[Depends(require_api_key)])
    def events(module: str | None = None, limit: int = 100, tag: str | None = None) -> list[dict[str, Any]]:
        return repo.list_events(module=module, limit=limit, tag=tag)

    @router.get("/alerts", dependencies=[Depends(require_api_key)])
    def alerts(limit: int = 100) -> list[dict[str, Any]]:
        return repo.list_alerts(limit=limit)

    @router.get("/analytics/summary", dependencies=[Depends(require_api_key)])
    def analytics_summary() -> dict[str, Any]:
        return repo.analytics_summary()

    @router.post("/demo/event", dependencies=[Depends(require_api_key)])
    def create_demo_event(module: str = "highway_surveillance", camera_id: str = "demo_webcam") -> dict[str, Any]:
        return repo.create_demo_event(module=module, camera_id=camera_id)

    @router.post("/demo/alert", dependencies=[Depends(require_api_key)])
    def create_demo_alert(module: str = "highway_surveillance", camera_id: str = "demo_webcam") -> dict[str, Any]:
        alert = Alert(
            module=module,
            camera_id=camera_id,
            title="Demo high-priority alert",
            message=f"Demo alert generated from dashboard at {int(time.time())}.",
            priority=AlertPriority.HIGH,
            metadata={"source": "dashboard_demo"},
        )
        row = repo.create_alert(alert)
        if isinstance(row, dict):
            return row
        return {
            "alert_id": row.alert_id,
            "module": row.module,
            "camera_id": row.camera_id,
            "title": row.title,
            "message": row.message,
            "priority": row.priority,
            "created_ts": row.created_ts,
        }

    @router.get("/cameras", dependencies=[Depends(require_api_key)])
    def cameras() -> list[dict[str, Any]]:
        return [asdict(health) for health in manager.health()]

    @router.get("/storage", dependencies=[Depends(require_api_key)])
    def storage() -> dict[str, Any]:
        root = Path(config.get("recording", {}).get("output_dir", "data/recordings"))
        usage = shutil.disk_usage(root if root.exists() else Path("."))
        size_bytes = sum(path.stat().st_size for path in root.rglob("*") if path.is_file()) if root.exists() else 0
        return {
            "recording_root": str(root),
            "recordings_bytes": size_bytes,
            "disk_total_bytes": usage.total,
            "disk_used_bytes": usage.used,
            "disk_free_bytes": usage.free,
        }

    @router.get("/events/{event_id}/clip", dependencies=[Depends(require_api_key)])
    def event_clip(event_id: str) -> FileResponse:
        for event in repo.list_events(limit=1000):
            if event["event_id"] == event_id and event.get("clip_path") and Path(event["clip_path"]).exists():
                return FileResponse(event["clip_path"], media_type="video/mp4")
        return FileResponse(Path("docs") / "no_clip.txt", media_type="text/plain")

    @router.websocket("/ws/live/{camera_id}")
    async def live_camera(websocket: WebSocket, camera_id: str) -> None:
        await websocket.accept()
        try:
            while True:
                ok, frame, ts = manager.read(camera_id)
                if ok and frame is not None:
                    _, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                    await websocket.send_text(
                        json.dumps(
                            {
                                "camera_id": camera_id,
                                "timestamp": ts,
                                "jpeg_base64": base64.b64encode(buffer).decode("ascii"),
                            }
                        )
                    )
                await asyncio.sleep(0.08)
        except WebSocketDisconnect:
            return

    @router.websocket("/ws/alerts")
    async def alert_stream(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                await websocket.send_text(json.dumps({"alerts": repo.list_alerts(limit=20)}))
                await asyncio.sleep(2.0)
        except WebSocketDisconnect:
            return

    return router
