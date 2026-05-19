"""Real-time YOLO inference and overlays for the dashboard live stream."""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from shared_core.ai_models.detector_base import Detection
from shared_core.ai_models.yolo_detector import YOLODetector
from shared_core.alert_engine.alerts import Alert, AlertPriority
from shared_core.database.repository import EventRepository
from shared_core.tracking_engine.tracker import TrackerFactory
from shared_core.utils.config import ROOT_DIR, load_config
from shared_core.vision.overlay import SECURITY_MODULES, VIOLATION_TAGS, annotate_frame

try:
    from highway_surveillance.detector import HighwayAnalytics, HighwayDetector
except ImportError:  # pragma: no cover
    HighwayAnalytics = None  # type: ignore[misc, assignment]
    HighwayDetector = None  # type: ignore[misc, assignment]


class LiveInferenceProcessor:
    """Module-aware live detector used by the dashboard WebSocket."""

    _cache: dict[str, "LiveInferenceProcessor"] = {}

    @classmethod
    def get(cls, module_name: str) -> "LiveInferenceProcessor":
        if module_name not in cls._cache:
            cls._cache[module_name] = cls(module_name)
        return cls._cache[module_name]

    def __init__(self, module_name: str) -> None:
        self.module_name = module_name
        module_config = ROOT_DIR / module_name / "config.yaml"
        self.config = load_config(module_config if module_config.exists() else None)
        ai_config = self.config.get("ai", {})
        self.speed_limit_kmph = float(self.config.get("rules", {}).get("speed_limit_kmph", 40.0))
        live_confidence = float(ai_config.get("confidence", 0.25))

        if module_name == "highway_surveillance" and HighwayDetector is not None and HighwayAnalytics is not None:
            self.detector = HighwayDetector(
                model_path=ai_config.get("model_path", "yolo11n.pt"),
                confidence=live_confidence,
                image_size=int(ai_config.get("image_size", 640)),
                device=ai_config.get("device", "auto"),
                use_half_precision=bool(ai_config.get("use_half_precision", True)),
                enable_night_vision=bool(self.config.get("rules", {}).get("night_vision_optimization", True)),
            )
            self.analytics = HighwayAnalytics.from_config(self.config)
        else:
            self.detector = YOLODetector(
                model_path=ai_config.get("model_path", "yolo11n.pt"),
                confidence=live_confidence,
                image_size=int(ai_config.get("image_size", 640)),
                device=ai_config.get("device", "auto"),
                use_half_precision=bool(ai_config.get("use_half_precision", True)),
            )
            self.analytics = None

        self.tracker = TrackerFactory.create(self.config.get("tracking", {}).get("type", "bytetrack"))
        self.repository = EventRepository.from_config(self.config)
        self._last_alert_by_key: dict[str, float] = {}
        self._frame_counter = 0
        self._warmup_detector()

    def _warmup_detector(self) -> None:
        try:
            self.detector._load()  # type: ignore[attr-defined]
        except Exception:
            pass

    def reset_tracking(self) -> None:
        """Clear track history after the camera is paused and resumed."""

        module_config = ROOT_DIR / self.module_name / "config.yaml"
        self.config = load_config(module_config if module_config.exists() else None)
        self.speed_limit_kmph = float(self.config.get("rules", {}).get("speed_limit_kmph", 80.0))
        if self.module_name == "highway_surveillance" and HighwayAnalytics is not None:
            self.analytics = HighwayAnalytics.from_config(self.config)
        elif self.analytics is not None:
            self.analytics.track_history.clear()
            self.analytics.stationary_since.clear()
        self.tracker = TrackerFactory.create(self.config.get("tracking", {}).get("type", "bytetrack"))

    def process(self, frame: np.ndarray, camera_id: str, timestamp: float | None = None) -> tuple[np.ndarray, dict[str, Any]]:
        timestamp = timestamp or time.time()
        self._frame_counter += 1
        detections = self.tracker.update(self.detector.detect(frame))
        analysis = self._build_analysis(detections, timestamp)
        if self.module_name == "highway_surveillance":
            self._dispatch_highway_alerts(camera_id, analysis, timestamp)
        annotated = annotate_frame(frame, self.module_name, analysis, speed_limit_kmph=self.speed_limit_kmph)
        summary = {
            "module": self.module_name,
            "camera_id": camera_id,
            "detection_count": len(analysis.get("vehicles", [])),
            "vehicle_count": analysis.get("vehicle_count", 0),
            "max_speed_kmph": analysis.get("max_speed_kmph"),
            "speed_limit_kmph": self.speed_limit_kmph if self.module_name == "highway_surveillance" else None,
            "tags": analysis.get("tags", []),
            "violations": sum(
                1
                for vehicle in analysis.get("vehicles", [])
                if set(vehicle.get("tags") or []) & VIOLATION_TAGS
                or (
                    self.module_name in SECURITY_MODULES
                    and vehicle.get("label", "").lower() == "person"
                )
            ),
        }
        return annotated, summary

    def _build_analysis(self, detections: list[Detection], timestamp: float) -> dict[str, Any]:
        if self.module_name == "highway_surveillance" and self.analytics is not None:
            analysis = self.analytics.analyze(detections, timestamp)
            analysis["speed_limit_kmph"] = self.speed_limit_kmph
            return analysis

        vehicles: list[dict[str, Any]] = []
        alert_count = 0
        for detection in detections:
            tags: list[str] = []
            if self.module_name in SECURITY_MODULES and detection.label.lower() == "person":
                tags.append("person_alert")
                alert_count += 1
            vehicles.append(
                {
                    "track_id": detection.tracker_id or -1,
                    "label": detection.label,
                    "confidence": round(detection.confidence, 4),
                    "bbox": detection.bbox,
                    "tags": tags,
                }
            )
        return {
            "tags": sorted({tag for vehicle in vehicles for tag in vehicle["tags"]}),
            "vehicle_count": len(vehicles),
            "vehicles": vehicles,
            "alert_count": alert_count,
        }

    def _dispatch_highway_alerts(self, camera_id: str, analysis: dict[str, Any], timestamp: float) -> None:
        cooldown = float(self.config.get("rules", {}).get("alert_cooldown_seconds", 30))
        high_priority_tags = {
            "speed_limit_warning": ("Speed limit exceeded", AlertPriority.HIGH),
            "wrong_way_detection": ("Wrong-way vehicle", AlertPriority.CRITICAL),
            "lane_violation_detection": ("Lane violation", AlertPriority.HIGH),
            "illegal_parking_detection": ("Illegal parking", AlertPriority.MEDIUM),
            "emergency_vehicle_prioritization": ("Emergency vehicle", AlertPriority.HIGH),
        }
        for tag in analysis.get("tags", []):
            if tag not in high_priority_tags:
                continue
            key = f"{camera_id}:{tag}"
            if timestamp - self._last_alert_by_key.get(key, 0.0) < cooldown:
                continue
            self._last_alert_by_key[key] = timestamp
            title, priority = high_priority_tags[tag]
            alert = Alert(
                module=self.module_name,
                camera_id=camera_id,
                title=title,
                message=f"{title} on {camera_id}. Max speed {analysis.get('max_speed_kmph', 0)} km/h (limit {self.speed_limit_kmph:.0f}).",
                priority=priority,
                metadata=analysis,
            )
            self.repository.create_alert(alert)
