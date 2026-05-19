"""Create SmartVision domain module starter files.

This script is part of the repository so future teams can regenerate a new
plug-in surveillance domain with the same contract as the built-in modules.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MODULES = {
    "highway_surveillance": {
        "title": "Highway Surveillance",
        "features": [
            "vehicle_detection",
            "speed_estimation",
            "speed_limit_warning",
            "wrong_way_detection",
            "lane_violation_detection",
            "accident_detection",
            "illegal_parking_detection",
            "number_plate_ocr",
            "emergency_vehicle_prioritization",
            "night_vision_optimization",
        ],
        "labels": ["car", "truck", "bus", "motorcycle", "bicycle", "person"],
    },
    "traffic_management": {
        "title": "Traffic Management",
        "features": [
            "traffic_density_estimation",
            "smart_signal_recommendation",
            "congestion_heatmaps",
            "vehicle_counting",
            "real_time_analytics",
            "traffic_flow_prediction",
            "adaptive_signal_timing",
            "peak_hour_analysis",
        ],
        "labels": ["car", "truck", "bus", "motorcycle", "bicycle"],
    },
    "smart_city_security": {
        "title": "Smart City Security",
        "features": [
            "suspicious_activity_detection",
            "abandoned_object_detection",
            "crowd_density_analysis",
            "loitering_detection",
            "fight_detection",
            "weapon_detection",
            "intrusion_detection",
            "restricted_zone_monitoring",
        ],
        "labels": ["person", "backpack", "handbag", "suitcase"],
    },
    "retail_analytics": {
        "title": "Retail Analytics",
        "features": [
            "customer_counting",
            "heatmap_generation",
            "queue_analysis",
            "shelf_monitoring",
            "theft_detection",
            "customer_movement_tracking",
            "staff_activity_analysis",
        ],
        "labels": ["person", "backpack", "handbag"],
    },
    "industrial_safety": {
        "title": "Industrial Safety",
        "features": [
            "ppe_detection",
            "fire_smoke_detection",
            "worker_fall_detection",
            "unsafe_zone_alerts",
            "machine_proximity_alerts",
            "hazard_monitoring",
        ],
        "labels": ["person", "helmet", "vest", "fire", "smoke"],
    },
    "smart_parking": {
        "title": "Smart Parking",
        "features": [
            "empty_slot_detection",
            "parking_occupancy_analytics",
            "illegal_parking_alerts",
            "anpr_integration",
            "parking_duration_tracking",
        ],
        "labels": ["car", "truck", "bus", "motorcycle"],
    },
    "railway_surveillance": {
        "title": "Railway Surveillance",
        "features": [
            "track_intrusion_detection",
            "human_detection_on_tracks",
            "platform_crowd_analysis",
            "unattended_baggage_detection",
        ],
        "labels": ["person", "backpack", "suitcase", "train"],
    },
    "campus_security": {
        "title": "Campus Security",
        "features": [
            "face_recognition_attendance",
            "unauthorized_entry_detection",
            "hostel_corridor_monitoring",
            "night_activity_detection",
        ],
        "labels": ["person", "backpack"],
    },
    "home_security": {
        "title": "Home Security",
        "features": [
            "human_detection",
            "pet_detection",
            "door_activity_monitoring",
            "intruder_alerts",
            "mobile_notification_system",
        ],
        "labels": ["person", "cat", "dog"],
    },
    "wildlife_monitoring": {
        "title": "Wildlife Monitoring",
        "features": [
            "animal_classification",
            "poacher_detection",
            "forest_fire_smoke_alerts",
            "zone_intrusion_alerts",
        ],
        "labels": ["person", "bird", "cat", "dog", "horse", "sheep", "cow", "bear", "zebra", "giraffe", "fire", "smoke"],
    },
}


def class_name(module_name: str) -> str:
    return "".join(part.capitalize() for part in module_name.split("_"))


def yaml_list(items: list[str], indent: int = 4) -> str:
    pad = " " * indent
    return "\n".join(f"{pad}- {item}" for item in items)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def module_config(module_name: str, meta: dict[str, object]) -> str:
    features = meta["features"]
    labels = meta["labels"]
    return f"""
module:
  name: {module_name}
  title: {meta["title"]}
  mode: edge
  offline_mode: true
  features:
{yaml_list(features)}

ai:
  model_path: yolo11n.pt
  confidence: 0.35
  image_size: 640
  device: auto
  use_half_precision: true
  target_labels:
{yaml_list(labels)}

cameras:
  - camera_id: {module_name}_demo
    name: {meta["title"]} Demo Camera
    source: "0"
    enabled: false
    fps: 15
    metadata:
      location: demo

motion:
  min_area: 900
  threshold: 25
  blur_kernel: 5
  history: 500
  var_threshold: 16.0
  detect_shadows: true
  scene_change_threshold: 0.35

recording:
  output_dir: {module_name}/recordings/clips
  snapshot_dir: {module_name}/recordings/snapshots
  pre_event_seconds: 4.0
  stop_timeout_seconds: 8.0
  target_fps: 12.0
  inactive_fps: 2.0
  codec: mp4v
  container: mp4
  min_event_score: 0.18
  snapshot_score_threshold: 0.08
  max_clip_seconds: 300.0

rules:
  alert_cooldown_seconds: 30
  restricted_zones: []
  count_lines: []
"""


def detector_py(module_name: str) -> str:
    cls = class_name(module_name)
    return f'''
"""Domain detector for {module_name}."""

from __future__ import annotations

from shared_core.ai_models.yolo_detector import YOLODetector


class {cls}Detector(YOLODetector):
    """YOLO-based detector placeholder for this surveillance domain."""

    pass
'''


def pipeline_py(module_name: str) -> str:
    cls = class_name(module_name)
    return f'''
"""Pipeline entrypoint for {module_name}."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from shared_core.ai_models.detector_base import Detection
from shared_core.module_runtime import DomainPipeline


class {cls}Pipeline(DomainPipeline):
    def __init__(self, config_path: str | Path | None = None) -> None:
        super().__init__("{module_name}", config_path or Path(__file__).with_name("config.yaml"))

    def analyze_detections(self, detections: list[Detection], frame: Any, timestamp: float) -> tuple[list[str], dict[str, Any]]:
        target_labels = set(self.config.get("ai", {{}}).get("target_labels", []))
        labels = [d.label for d in detections if not target_labels or d.label in target_labels]
        tags = sorted(set(labels))
        return tags, {{
            "object_count": len(labels),
            "labels": tags,
            "features": self.config.get("module", {{}}).get("features", []),
        }}
'''


def api_py(module_name: str, meta: dict[str, object]) -> str:
    title = meta["title"]
    return f'''
"""FastAPI routes for the {title} module."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends

from shared_core.dashboard.auth import require_api_key
from shared_core.database.repository import EventRepository
from shared_core.utils.config import load_config


MODULE_NAME = "{module_name}"
CONFIG_PATH = Path(__file__).with_name("config.yaml")
router = APIRouter(prefix="/api/modules/{module_name}", tags=["{title}"])


@router.get("/health")
def health() -> dict[str, Any]:
    return {{"module": MODULE_NAME, "status": "ready", "config": str(CONFIG_PATH)}}


@router.get("/features")
def features() -> dict[str, Any]:
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    return {{"module": MODULE_NAME, "features": data.get("module", {{}}).get("features", [])}}


@router.get("/config", dependencies=[Depends(require_api_key)])
def config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


@router.get("/events", dependencies=[Depends(require_api_key)])
def events(limit: int = 50) -> list[dict[str, Any]]:
    return EventRepository.from_config(load_config(CONFIG_PATH)).list_events(module=MODULE_NAME, limit=limit)
'''


def alerts_py(module_name: str) -> str:
    cls = class_name(module_name)
    return f'''
"""Alert rules for {module_name}."""

from __future__ import annotations

from shared_core.alert_engine.alerts import Alert, AlertPriority


def build_event_alert(camera_id: str, title: str, message: str, event_id: str | None = None, priority: AlertPriority = AlertPriority.MEDIUM) -> Alert:
    return Alert(module="{module_name}", camera_id=camera_id, title=title, message=message, event_id=event_id, priority=priority)


class {cls}AlertRules:
    def classify_priority(self, tags: list[str], score: float) -> AlertPriority:
        if score >= 0.80:
            return AlertPriority.CRITICAL
        if score >= 0.60:
            return AlertPriority.HIGH
        if tags:
            return AlertPriority.MEDIUM
        return AlertPriority.LOW
'''


def service_py(module_name: str) -> str:
    cls = class_name(module_name)
    return f'''
"""Run this surveillance domain as an independent service.

Usage:
    python -m {module_name}.service
"""

from __future__ import annotations

from {module_name}.pipeline import {cls}Pipeline


def main() -> None:
    {cls}Pipeline().run()


if __name__ == "__main__":
    main()
'''


def readme_md(module_name: str, meta: dict[str, object]) -> str:
    features = "\n".join(f"- {feature}" for feature in meta["features"])
    return f"""
# {meta["title"]}

Independent SmartVision AI service for `{module_name}`.

## Features

{features}

## Run

```bash
python -m {module_name}.service
```

The module uses its local `config.yaml`, writes logs under `logs/`, and stores
event clips/snapshots under `recordings/`.
"""


def requirements_txt() -> str:
    return """
-r ../requirements.txt
"""


def scaffold() -> None:
    for module_name, meta in MODULES.items():
        module_dir = ROOT / module_name
        write(module_dir / "__init__.py", f'"""SmartVision domain module: {module_name}."""')
        write(module_dir / "config.yaml", module_config(module_name, meta))
        write(module_dir / "detector.py", detector_py(module_name))
        write(module_dir / "pipeline.py", pipeline_py(module_name))
        write(module_dir / "api.py", api_py(module_name, meta))
        write(module_dir / "alerts.py", alerts_py(module_name))
        write(module_dir / "service.py", service_py(module_name))
        write(module_dir / "requirements.txt", requirements_txt())
        write(module_dir / "README.md", readme_md(module_name, meta))
        for keep in [
            module_dir / "logs" / ".gitkeep",
            module_dir / "recordings" / "clips" / ".gitkeep",
            module_dir / "recordings" / "snapshots" / ".gitkeep",
        ]:
            write(keep, "")


if __name__ == "__main__":
    scaffold()
