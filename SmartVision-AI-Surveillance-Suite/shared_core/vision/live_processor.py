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
        target_labels = ai_config.get("target_labels") or []

        if module_name == "highway_surveillance" and HighwayDetector is not None and HighwayAnalytics is not None:
            self.detector = HighwayDetector(
                model_path=ai_config.get("model_path", "yolo11n.pt"),
                confidence=live_confidence,
                image_size=int(ai_config.get("image_size", 640)),
                device=ai_config.get("device", "auto"),
                use_half_precision=bool(ai_config.get("use_half_precision", True)),
                target_labels=target_labels,
                iou=float(ai_config.get("iou", 0.45)),
                max_detections=int(ai_config.get("max_detections", 100)),
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
                target_labels=target_labels,
                iou=float(ai_config.get("iou", 0.45)),
                max_detections=int(ai_config.get("max_detections", 100)),
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
        messages = self._build_messages(camera_id, analysis)
        self._dispatch_alerts(camera_id, analysis, messages, timestamp)
        annotated = annotate_frame(frame, self.module_name, analysis, speed_limit_kmph=self.speed_limit_kmph)
        summary = {
            "module": self.module_name,
            "camera_id": camera_id,
            "detection_count": len(analysis.get("vehicles", [])),
            "vehicle_count": analysis.get("vehicle_count", 0),
            "max_speed_kmph": analysis.get("max_speed_kmph"),
            "speed_limit_kmph": self.speed_limit_kmph if self.module_name == "highway_surveillance" else None,
            "tags": analysis.get("tags", []),
            "messages": messages,
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

    def _build_messages(self, camera_id: str, analysis: dict[str, Any]) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        module_title = self.module_name.replace("_", " ").title()
        vehicles = analysis.get("vehicles", [])
        tags = set(analysis.get("tags", []))

        def add(title: str, message: str, priority: str = "info", tag: str = "status") -> None:
            messages.append({"title": title, "message": message, "priority": priority, "tag": tag, "camera_id": camera_id})

        if self.module_name == "highway_surveillance":
            for vehicle in vehicles:
                label = vehicle.get("label", "Vehicle")
                speed = float(vehicle.get("speed_kmph") or 0)
                vehicle_tags = set(vehicle.get("tags") or [])
                track = vehicle.get("track_id", "-")
                if "speed_limit_warning" in vehicle_tags:
                    add("Speed limit crossed", f"{label} track {track} reached {speed:.0f} km/h over the {self.speed_limit_kmph:.0f} km/h limit.", "critical", "speed_limit_warning")
                if "wrong_way_detection" in vehicle_tags:
                    add("Wrong-way movement", f"{label} track {track} is moving against the configured traffic direction.", "critical", "wrong_way_detection")
                if "lane_violation_detection" in vehicle_tags:
                    add("Lane zone violation", f"{label} track {track} moved outside the allowed lane zone.", "warning", "lane_violation_detection")
                if "illegal_parking_detection" in vehicle_tags:
                    add("Illegal parking", f"{label} track {track} has stayed almost stationary inside the scene.", "warning", "illegal_parking_detection")
            if not messages:
                add("Highway flow normal", f"{analysis.get('vehicle_count', 0)} vehicles tracked. Max speed {analysis.get('max_speed_kmph', 0):.0f} km/h.", "ok")
            return messages[:6]

        if self.module_name == "traffic_management":
            count = analysis.get("vehicle_count", len(vehicles))
            if count >= 8:
                add("Heavy congestion", f"{count} road users are visible. Consider longer green time for this approach.", "warning", "traffic_density")
            elif count >= 4:
                add("Moderate traffic", f"{count} vehicles detected with steady flow.", "info", "traffic_density")
            else:
                add("Road segment clear", f"{count} vehicles currently detected.", "ok", "traffic_density")
            return messages

        if self.module_name == "smart_parking":
            parked = [v for v in vehicles if v.get("label", "").lower() in {"car", "truck", "bus", "motorcycle"}]
            add("Parking occupancy", f"{len(parked)} parked or moving vehicles visible in the lot.", "info", "parking_occupancy")
            if len(parked) >= 10:
                add("Lot nearly full", "Detected occupancy is high for the current view.", "warning", "parking_full")
            return messages

        if self.module_name == "retail_analytics":
            people = [v for v in vehicles if v.get("label", "").lower() == "person"]
            add("Customer movement", f"{len(people)} shoppers detected in the monitored area.", "info", "footfall")
            if len(people) >= 6:
                add("Crowded aisle", "Footfall is high; review queue or staff allocation.", "warning", "crowding")
            return messages

        if self.module_name in SECURITY_MODULES:
            people = [v for v in vehicles if v.get("label", "").lower() == "person"]
            if people:
                label = {
                    "home_security": "Person detected near home camera",
                    "campus_security": "Unauthorized presence candidate",
                    "smart_city_security": "Public-area person activity",
                    "industrial_safety": "Worker/person detected in safety view",
                    "railway_surveillance": "Person detected near rail zone",
                    "wildlife_monitoring": "Human activity candidate in wildlife zone",
                }.get(self.module_name, "Person detected")
                add(label, f"{len(people)} person track(s) detected on {camera_id}.", "critical", "person_alert")
            else:
                add(f"{module_title} clear", "No person-triggered alert in the current frame.", "ok")
            return messages

        if vehicles:
            add("Objects detected", f"{len(vehicles)} tracked object(s): {', '.join(sorted({v.get('label', 'object') for v in vehicles})[:4])}.", "info")
        else:
            add(f"{module_title} clear", "No tracked objects in the current frame.", "ok")
        return messages

    def _dispatch_alerts(self, camera_id: str, analysis: dict[str, Any], messages: list[dict[str, Any]], timestamp: float) -> None:
        cooldown = float(self.config.get("rules", {}).get("alert_cooldown_seconds", 30))
        priority_by_name = {"ok": AlertPriority.LOW, "info": AlertPriority.MEDIUM, "warning": AlertPriority.HIGH, "critical": AlertPriority.CRITICAL}
        high_priority_tags = {
            "speed_limit_warning": ("Speed limit exceeded", AlertPriority.HIGH),
            "wrong_way_detection": ("Wrong-way vehicle", AlertPriority.CRITICAL),
            "lane_violation_detection": ("Lane violation", AlertPriority.HIGH),
            "illegal_parking_detection": ("Illegal parking", AlertPriority.MEDIUM),
            "emergency_vehicle_prioritization": ("Emergency vehicle", AlertPriority.HIGH),
            "person_alert": ("Person activity", AlertPriority.HIGH),
            "traffic_density": ("Traffic density change", AlertPriority.MEDIUM),
            "parking_full": ("Parking occupancy high", AlertPriority.HIGH),
            "crowding": ("Crowding detected", AlertPriority.HIGH),
        }
        for item in messages:
            tag = item.get("tag", "status")
            if tag not in high_priority_tags and item.get("priority") not in {"warning", "critical"}:
                continue
            key = f"{camera_id}:{tag}"
            if timestamp - self._last_alert_by_key.get(key, 0.0) < cooldown:
                continue
            self._last_alert_by_key[key] = timestamp
            default_title, default_priority = high_priority_tags.get(tag, (item.get("title", "Tracking alert"), priority_by_name.get(item.get("priority"), AlertPriority.MEDIUM)))
            alert = Alert(
                module=self.module_name,
                camera_id=camera_id,
                title=item.get("title") or default_title,
                message=item.get("message") or default_title,
                priority=default_priority,
                metadata=analysis,
            )
            self.repository.create_alert(alert)
