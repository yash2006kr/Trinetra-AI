"""MongoDB repository implementation for cloud-style metadata storage."""

from __future__ import annotations

from pathlib import Path
from time import time
from typing import Any
from uuid import uuid4

from shared_core.alert_engine.alerts import Alert
from shared_core.recording_engine.event_recorder import RecordingEvent


class MongoEventRepository:
    """Duck-compatible repository used when DATABASE_URL starts with mongodb."""

    def __init__(self, database_url: str, database_name: str = "smartvision_ai_surveillance_suite") -> None:
        from pymongo import MongoClient

        self.client = MongoClient(database_url, serverSelectionTimeoutMS=8000)
        self.db = self.client[database_name]
        self.cameras = self.db["cameras"]
        self.events = self.db["events"]
        self.alerts = self.db["alerts"]
        self.health = self.db["module_health"]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self.cameras.create_index("camera_id", unique=True)
        self.events.create_index("event_id", unique=True)
        self.events.create_index([("module", 1), ("start_ts", -1)])
        self.events.create_index("camera_id")
        self.alerts.create_index("alert_id", unique=True)
        self.alerts.create_index([("created_ts", -1)])

    def upsert_camera(self, camera_id: str, source: str, module: str | None = None, name: str | None = None, metadata: dict[str, Any] | None = None) -> None:
        self.cameras.update_one(
            {"camera_id": camera_id},
            {
                "$set": {
                    "camera_id": camera_id,
                    "source": source,
                    "module": module,
                    "name": name,
                    "enabled": True,
                    "metadata": metadata or {},
                }
            },
            upsert=True,
        )

    def create_event_from_recording(self, event: RecordingEvent) -> dict[str, Any]:
        end_ts = event.last_motion_ts
        row = {
            "event_id": event.event_id,
            "module": event.module_name,
            "camera_id": event.camera_id,
            "clip_path": str(event.clip_path),
            "snapshot_path": None,
            "start_ts": event.start_ts,
            "end_ts": end_ts,
            "duration_seconds": max(0.0, end_ts - event.start_ts),
            "score": event.score,
            "tags": sorted(event.tags),
            "metadata": {"metadata_path": str(event.metadata_path), "frame_count": event.frame_count},
        }
        self.events.update_one({"event_id": event.event_id}, {"$set": row}, upsert=True)
        return row

    def create_alert(self, alert: Alert) -> dict[str, Any]:
        row = {
            "alert_id": alert.alert_id,
            "event_id": alert.event_id,
            "module": alert.module,
            "camera_id": alert.camera_id,
            "title": alert.title,
            "message": alert.message,
            "priority": int(alert.priority),
            "metadata": alert.metadata,
            "created_ts": alert.created_ts,
            "acknowledged": False,
        }
        self.alerts.update_one({"alert_id": alert.alert_id}, {"$set": row}, upsert=True)
        return row

    def create_demo_event(self, module: str = "highway_surveillance", camera_id: str = "demo_webcam") -> dict[str, Any]:
        now = time()
        row = {
            "event_id": uuid4().hex,
            "module": module,
            "camera_id": camera_id,
            "clip_path": None,
            "snapshot_path": None,
            "start_ts": now,
            "end_ts": now + 4.0,
            "duration_seconds": 4.0,
            "score": 0.72,
            "tags": ["demo_event", "vehicle_detection", "motion"],
            "metadata": {"source": "dashboard_demo"},
        }
        self.events.insert_one(row)
        row.pop("_id", None)
        return self._event_dict(row)

    def list_events(self, module: str | None = None, limit: int = 100, tag: str | None = None) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if module:
            query["module"] = module
        if tag:
            query["tags"] = tag
        rows = self.events.find(query, {"_id": 0}).sort("start_ts", -1).limit(limit)
        return [self._event_dict(row) for row in rows]

    def list_alerts(self, limit: int = 100) -> list[dict[str, Any]]:
        return list(self.alerts.find({}, {"_id": 0}).sort("created_ts", -1).limit(limit))

    def analytics_summary(self) -> dict[str, Any]:
        modules = self.events.aggregate([{"$group": {"_id": "$module", "count": {"$sum": 1}}}])
        return {
            "total_events": self.events.count_documents({}),
            "high_priority_events": self.events.count_documents({"score": {"$gte": 0.65}}),
            "events_by_module": {row["_id"]: row["count"] for row in modules if row["_id"]},
        }

    def _event_dict(self, row: dict[str, Any]) -> dict[str, Any]:
        clip_path = row.get("clip_path")
        return {
            "event_id": row.get("event_id"),
            "module": row.get("module"),
            "camera_id": row.get("camera_id"),
            "clip_path": clip_path,
            "snapshot_path": row.get("snapshot_path"),
            "start_ts": row.get("start_ts"),
            "end_ts": row.get("end_ts"),
            "duration_seconds": row.get("duration_seconds"),
            "score": row.get("score", 0),
            "tags": row.get("tags", []),
            "metadata": row.get("metadata", {}),
            "clip_exists": bool(clip_path and Path(clip_path).exists()),
        }
