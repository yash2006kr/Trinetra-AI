"""Repository functions used by pipelines and dashboard APIs."""

from __future__ import annotations

from pathlib import Path
from time import time
from typing import Any
from uuid import uuid4

from sqlalchemy import desc, func, select

from shared_core.alert_engine.alerts import Alert
from shared_core.database.models import AlertRecord, Camera, Event
from shared_core.database.session import build_session_factory
from shared_core.recording_engine.event_recorder import RecordingEvent


class EventRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.session_factory = build_session_factory(database_url)

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> Any:
        app_config = config.get("app", {})
        database_url = app_config.get("database_url", "sqlite:///data/smartvision.db")
        if database_url.startswith("mongodb"):
            from shared_core.database.mongo_repository import MongoEventRepository

            return MongoEventRepository(database_url, app_config.get("database_name", "smartvision_ai_surveillance_suite"))
        return cls(database_url)

    def upsert_camera(self, camera_id: str, source: str, module: str | None = None, name: str | None = None, metadata: dict[str, Any] | None = None) -> None:
        with self.session_factory() as session:
            camera = session.get(Camera, camera_id)
            if not camera:
                camera = Camera(camera_id=camera_id, source=source, module=module, name=name, metadata_json=metadata or {})
                session.add(camera)
            else:
                camera.source = source
                camera.module = module or camera.module
                camera.name = name or camera.name
                camera.metadata_json = metadata or camera.metadata_json
            session.commit()

    def create_event_from_recording(self, event: RecordingEvent) -> Event:
        end_ts = event.last_motion_ts
        with self.session_factory() as session:
            camera = session.get(Camera, event.camera_id)
            if not camera:
                camera = Camera(camera_id=event.camera_id, module=event.module_name, source="unknown", enabled=True)
                session.add(camera)
                session.flush()
            row = Event(
                event_id=event.event_id,
                module=event.module_name,
                camera_id=event.camera_id,
                clip_path=str(event.clip_path),
                start_ts=event.start_ts,
                end_ts=end_ts,
                duration_seconds=max(0.0, end_ts - event.start_ts),
                score=event.score,
                tags=sorted(event.tags),
                metadata_json={"metadata_path": str(event.metadata_path), "frame_count": event.frame_count},
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row

    def create_alert(self, alert: Alert) -> AlertRecord:
        with self.session_factory() as session:
            row = AlertRecord(
                alert_id=alert.alert_id,
                event_id=alert.event_id,
                module=alert.module,
                camera_id=alert.camera_id,
                title=alert.title,
                message=alert.message,
                priority=int(alert.priority),
                metadata_json=alert.metadata,
                created_ts=alert.created_ts,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row

    def create_demo_event(self, module: str = "highway_surveillance", camera_id: str = "demo_webcam") -> dict[str, Any]:
        event_id = uuid4().hex
        now = time()
        with self.session_factory() as session:
            camera = session.get(Camera, camera_id)
            if not camera:
                camera = Camera(camera_id=camera_id, module=module, source="0", enabled=True, name="Local Webcam")
                session.add(camera)
                session.flush()
            row = Event(
                event_id=event_id,
                module=module,
                camera_id=camera_id,
                clip_path=None,
                snapshot_path=None,
                start_ts=now,
                end_ts=now + 4.0,
                duration_seconds=4.0,
                score=0.72,
                tags=["demo_event", "vehicle_detection", "motion"],
                metadata_json={"source": "dashboard_demo"},
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._event_dict(row)

    def list_events(self, module: str | None = None, limit: int = 100, tag: str | None = None) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            query = select(Event).order_by(desc(Event.start_ts)).limit(limit)
            if module:
                query = query.where(Event.module == module)
            rows = list(session.scalars(query))
            if tag:
                rows = [row for row in rows if tag in (row.tags or [])]
            return [self._event_dict(row) for row in rows]

    def list_alerts(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            rows = list(session.scalars(select(AlertRecord).order_by(desc(AlertRecord.created_ts)).limit(limit)))
            return [
                {
                    "alert_id": row.alert_id,
                    "event_id": row.event_id,
                    "module": row.module,
                    "camera_id": row.camera_id,
                    "title": row.title,
                    "message": row.message,
                    "priority": row.priority,
                    "metadata": row.metadata_json or {},
                    "created_ts": row.created_ts,
                    "acknowledged": row.acknowledged,
                }
                for row in rows
            ]

    def analytics_summary(self) -> dict[str, Any]:
        with self.session_factory() as session:
            total_events = session.scalar(select(func.count(Event.id))) or 0
            high_priority = session.scalar(select(func.count(Event.id)).where(Event.score >= 0.65)) or 0
            modules = session.execute(select(Event.module, func.count(Event.id)).group_by(Event.module)).all()
            return {
                "total_events": total_events,
                "high_priority_events": high_priority,
                "events_by_module": {module: count for module, count in modules},
            }

    def _event_dict(self, row: Event) -> dict[str, Any]:
        return {
            "event_id": row.event_id,
            "module": row.module,
            "camera_id": row.camera_id,
            "clip_path": row.clip_path,
            "snapshot_path": row.snapshot_path,
            "start_ts": row.start_ts,
            "end_ts": row.end_ts,
            "duration_seconds": row.duration_seconds,
            "score": row.score,
            "tags": row.tags or [],
            "metadata": row.metadata_json or {},
            "clip_exists": bool(row.clip_path and Path(row.clip_path).exists()),
        }
