"""Dashboard REST and WebSocket routes."""

from __future__ import annotations

import asyncio
import base64
import json
import shutil
import time
from uuid import uuid4
from dataclasses import asdict
from pathlib import Path
from typing import Any

import cv2
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from shared_core.alert_engine.alerts import Alert, AlertPriority
from shared_core.dashboard.auth import require_api_key
from shared_core.database.repository import EventRepository
from shared_core.stream_manager.camera_manager import CameraManager
from shared_core.utils.config import load_config
from shared_core.vision.live_processor import LiveInferenceProcessor


def create_dashboard_router(camera_manager: CameraManager | None = None, repository: EventRepository | None = None) -> APIRouter:
    config = load_config()
    repo = repository or EventRepository.from_config(config)
    manager = camera_manager or CameraManager()
    camera_catalog = {item["camera_id"]: item for item in config.get("cameras", [])}
    video_jobs: dict[str, Path] = {}
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

    @router.post("/videos", dependencies=[Depends(require_api_key)])
    async def upload_video(file: UploadFile = File(...)) -> dict[str, Any]:
        suffix = Path(file.filename or "sample.mp4").suffix.lower()
        if suffix not in {".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v"}:
            raise HTTPException(status_code=400, detail="Unsupported video format")
        upload_dir = Path("data") / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        job_id = uuid4().hex
        target = upload_dir / f"{job_id}{suffix}"
        with target.open("wb") as handle:
            while chunk := await file.read(1024 * 1024):
                handle.write(chunk)
        video_jobs[job_id] = target
        return {"job_id": job_id, "filename": file.filename, "path": str(target)}

    @router.get("/cameras", dependencies=[Depends(require_api_key)])
    def cameras() -> list[dict[str, Any]]:
        health_by_id = {health.camera_id: health for health in manager.health()}
        active_id = manager.active_camera_id()
        rows: list[dict[str, Any]] = []
        for camera_id, raw in camera_catalog.items():
            health = health_by_id.get(camera_id)
            rows.append(
                {
                    "camera_id": camera_id,
                    "name": raw.get("name") or camera_id,
                    "source": str(raw.get("source", "")),
                    "running": health.running if health else False,
                    "connected": health.connected if health else False,
                    "last_frame_ts": health.last_frame_ts if health else None,
                    "frames_read": health.frames_read if health else 0,
                    "failures": health.failures if health else 0,
                    "active": camera_id == active_id,
                }
            )
        if not rows:
            return [asdict(health) for health in manager.health()]
        return rows

    @router.post("/cameras/{camera_id}/activate", dependencies=[Depends(require_api_key)])
    def activate_camera(camera_id: str, module: str = "highway_surveillance") -> dict[str, Any]:
        activated = manager.activate_only(camera_id)
        if activated:
            LiveInferenceProcessor.get(module).reset_tracking()
        return {"camera_id": camera_id, "activated": activated, "active": manager.active_camera_id()}

    @router.post("/cameras/{camera_id}/pause", dependencies=[Depends(require_api_key)])
    def pause_camera(camera_id: str) -> dict[str, Any]:
        paused = manager.pause(camera_id)
        return {"camera_id": camera_id, "paused": paused}

    @router.post("/cameras/{camera_id}/resume", dependencies=[Depends(require_api_key)])
    def resume_camera(camera_id: str, module: str = "highway_surveillance") -> dict[str, Any]:
        resumed = manager.resume(camera_id)
        if resumed:
            LiveInferenceProcessor.get(module).reset_tracking()
        return {"camera_id": camera_id, "resumed": resumed}

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
        """Plain webcam stream without AI overlays."""

        await websocket.accept()
        try:
            while True:
                health = next((item for item in manager.health() if item.camera_id == camera_id), None)
                if health is None or not health.running:
                    await websocket.send_text(json.dumps({"camera_id": camera_id, "paused": True}))
                    await asyncio.sleep(0.3)
                    continue

                ok, frame, ts = manager.read(camera_id)
                if ok and frame is not None:
                    _, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                    await websocket.send_text(
                        json.dumps(
                            {
                                "camera_id": camera_id,
                                "timestamp": ts,
                                "paused": False,
                                "jpeg_base64": base64.b64encode(buffer).decode("ascii"),
                            }
                        )
                    )
                await asyncio.sleep(0.05)
        except WebSocketDisconnect:
            return

    @router.websocket("/ws/tracking/{camera_id}")
    async def tracking_camera(websocket: WebSocket, camera_id: str, module: str = "highway_surveillance") -> None:
        """YOLO + OpenCV annotated stream for the active surveillance module."""

        await websocket.accept()
        processor = LiveInferenceProcessor.get(module)
        try:
            while True:
                health = next((item for item in manager.health() if item.camera_id == camera_id), None)
                if health is None or not health.running:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "camera_id": camera_id,
                                "module": module,
                                "paused": True,
                                "detections": None,
                            }
                        )
                    )
                    await asyncio.sleep(0.3)
                    continue

                ok, frame, ts = manager.read(camera_id)
                if ok and frame is not None:
                    output = frame
                    detection_summary: dict[str, Any] = {"detection_count": 0, "model_ready": processor.detector.loaded}
                    try:
                        if not processor.detector.loaded:
                            ok_preview, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                            if ok_preview:
                                await websocket.send_text(
                                    json.dumps(
                                        {
                                            "camera_id": camera_id,
                                            "module": module,
                                            "timestamp": ts,
                                            "paused": False,
                                            "jpeg_base64": base64.b64encode(buf).decode("ascii"),
                                            "detections": {"detection_count": 0, "loading": True},
                                        }
                                    )
                                )
                        output, detection_summary = await asyncio.to_thread(processor.process, frame, camera_id, ts)
                        detection_summary["model_ready"] = True
                        detection_summary.pop("loading", None)
                    except Exception as exc:
                        output = frame.copy()
                        cv2.putText(
                            output,
                            f"Detection error: {exc}"[:80],
                            (12, 28),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.55,
                            (0, 0, 255),
                            2,
                            cv2.LINE_AA,
                        )
                        detection_summary = {"detection_count": 0, "error": str(exc), "model_ready": False}
                    _, buffer = cv2.imencode(".jpg", output, [int(cv2.IMWRITE_JPEG_QUALITY), 72])
                    await websocket.send_text(
                        json.dumps(
                            {
                                "camera_id": camera_id,
                                "module": module,
                                "timestamp": ts,
                                "paused": False,
                                "jpeg_base64": base64.b64encode(buffer).decode("ascii"),
                                "detections": detection_summary,
                            }
                        )
                    )
                await asyncio.sleep(0.05)
        except WebSocketDisconnect:
            return

    @router.websocket("/ws/video/{job_id}")
    async def video_tracking(websocket: WebSocket, job_id: str, module: str = "highway_surveillance") -> None:
        """Run the same live detector over an uploaded video file and stream annotated frames."""

        await websocket.accept()
        path = video_jobs.get(job_id)
        if not path or not path.exists():
            await websocket.send_text(json.dumps({"job_id": job_id, "error": "Uploaded video was not found"}))
            await websocket.close()
            return

        processor = LiveInferenceProcessor.get(module)
        processor.reset_tracking()
        capture = cv2.VideoCapture(str(path))
        fps = capture.get(cv2.CAP_PROP_FPS) or 15.0
        frame_delay = min(0.12, max(0.025, 1.0 / max(fps, 1.0)))
        frame_index = 0
        try:
            while True:
                ok, frame = capture.read()
                if not ok or frame is None:
                    await websocket.send_text(json.dumps({"job_id": job_id, "module": module, "complete": True}))
                    break
                timestamp = time.time()
                output = frame
                detection_summary: dict[str, Any] = {"detection_count": 0, "model_ready": processor.detector.loaded}
                try:
                    output, detection_summary = await asyncio.to_thread(processor.process, frame, f"file_{job_id[:8]}", timestamp)
                    detection_summary["model_ready"] = True
                    detection_summary["frame_index"] = frame_index
                    detection_summary["source"] = "uploaded_video"
                except Exception as exc:
                    output = frame.copy()
                    cv2.putText(output, f"Detection error: {exc}"[:80], (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2, cv2.LINE_AA)
                    detection_summary = {"detection_count": 0, "error": str(exc), "model_ready": False, "frame_index": frame_index}
                _, buffer = cv2.imencode(".jpg", output, [int(cv2.IMWRITE_JPEG_QUALITY), 72])
                await websocket.send_text(
                    json.dumps(
                        {
                            "job_id": job_id,
                            "module": module,
                            "timestamp": timestamp,
                            "complete": False,
                            "jpeg_base64": base64.b64encode(buffer).decode("ascii"),
                            "detections": detection_summary,
                        }
                    )
                )
                frame_index += 1
                await asyncio.sleep(frame_delay)
        except WebSocketDisconnect:
            return
        finally:
            capture.release()

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
