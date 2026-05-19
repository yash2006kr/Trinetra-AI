"""Fully working reference pipeline for highway surveillance."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from shared_core.ai_models.detector_base import Detection
from shared_core.alert_engine.alerts import Alert, AlertPriority
from shared_core.module_runtime import DomainPipeline

from highway_surveillance.detector import HighwayAnalytics, HighwayDetector


class HighwaySurveillancePipeline(DomainPipeline):
    def __init__(self, config_path: str | Path | None = None) -> None:
        super().__init__("highway_surveillance", config_path or Path(__file__).with_name("config.yaml"))
        ai_config = self.config.get("ai", {})
        self.detector = HighwayDetector(
            model_path=ai_config.get("model_path", "yolo11n.pt"),
            confidence=float(ai_config.get("confidence", 0.35)),
            image_size=int(ai_config.get("image_size", 640)),
            device=ai_config.get("device", "auto"),
            use_half_precision=bool(ai_config.get("use_half_precision", True)),
            enable_night_vision=bool(self.config.get("rules", {}).get("night_vision_optimization", True)),
        )
        self.analytics = HighwayAnalytics.from_config(self.config)
        self._last_alert_by_key: dict[str, float] = {}

    def analyze_detections(self, detections: list[Detection], frame: Any, timestamp: float, camera_id: str | None = None) -> tuple[list[str], dict[str, Any]]:
        analysis = self.analytics.analyze(detections, timestamp)
        camera_id = camera_id or "unknown"
        self._dispatch_rule_alerts(camera_id, analysis, timestamp)
        return analysis["tags"], analysis

    def _dispatch_rule_alerts(self, camera_id: str, analysis: dict[str, Any], timestamp: float) -> None:
        cooldown = float(self.config.get("rules", {}).get("alert_cooldown_seconds", 30))
        high_priority_tags = {
            "speed_limit_warning": ("Speed limit warning", AlertPriority.HIGH),
            "wrong_way_detection": ("Wrong-way vehicle", AlertPriority.CRITICAL),
            "lane_violation_detection": ("Lane violation", AlertPriority.HIGH),
            "illegal_parking_detection": ("Illegal parking", AlertPriority.MEDIUM),
            "emergency_vehicle_prioritization": ("Emergency vehicle priority", AlertPriority.HIGH),
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
                module="highway_surveillance",
                camera_id=camera_id,
                title=title,
                message=f"{title} detected on {camera_id}. Max speed: {analysis.get('max_speed_kmph', 0)} km/h.",
                priority=priority,
                metadata=analysis,
            )
            self.alerts.dispatch(alert)
            self.repository.create_alert(alert)
