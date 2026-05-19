"""Highway-specific detection and analytics helpers."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from shared_core.ai_models.detector_base import Detection
from shared_core.ai_models.yolo_detector import YOLODetector
from shared_core.utils.geometry import bbox_center, point_in_polygon


VEHICLE_LABELS = {"car", "truck", "bus", "motorcycle", "bicycle"}


@dataclass(slots=True)
class HighwayRuleConfig:
    speed_limit_kmph: float = 80.0
    pixels_per_meter: float = 12.0
    allowed_direction: tuple[float, float] = (1.0, 0.0)
    wrong_way_min_displacement_px: float = 35.0
    illegal_parking_seconds: float = 45.0
    parked_speed_threshold_kmph: float = 3.0
    lane_zones: list[list[tuple[float, float]]] = field(default_factory=list)
    emergency_labels: set[str] = field(default_factory=lambda: {"ambulance", "fire truck", "police car"})


class HighwayDetector(YOLODetector):
    """YOLO detector with highway-oriented preprocessing and filtering."""

    def __init__(self, *args: Any, enable_night_vision: bool = True, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.enable_night_vision = enable_night_vision

    def detect(self, frame: np.ndarray) -> list[Detection]:
        processed = self.optimize_night_frame(frame) if self.enable_night_vision else frame
        detections = super().detect(processed)
        return [d for d in detections if d.label.lower() in VEHICLE_LABELS or d.label.lower() == "person"]

    @staticmethod
    def optimize_night_frame(frame: np.ndarray) -> np.ndarray:
        """Improve low-light contrast using CLAHE on luminance."""

        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
        enhanced_l = clahe.apply(l_channel)
        enhanced = cv2.merge((enhanced_l, a_channel, b_channel))
        return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)


class HighwayAnalytics:
    """Stateful highway rules that operate on tracked detections."""

    def __init__(self, rules: HighwayRuleConfig | None = None) -> None:
        self.rules = rules or HighwayRuleConfig()
        self.track_history: dict[int, deque[tuple[float, tuple[float, float]]]] = defaultdict(lambda: deque(maxlen=20))
        self.stationary_since: dict[int, float] = {}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "HighwayAnalytics":
        rules = config.get("rules", {})
        direction = tuple(rules.get("allowed_direction", [1.0, 0.0]))
        lane_zones = [
            [tuple(point) for point in zone]
            for zone in rules.get("lane_zones", [])
        ]
        return cls(
            HighwayRuleConfig(
                speed_limit_kmph=float(rules.get("speed_limit_kmph", 80.0)),
                pixels_per_meter=float(rules.get("pixels_per_meter", 12.0)),
                allowed_direction=(float(direction[0]), float(direction[1])),
                wrong_way_min_displacement_px=float(rules.get("wrong_way_min_displacement_px", 35.0)),
                illegal_parking_seconds=float(rules.get("illegal_parking_seconds", 45.0)),
                parked_speed_threshold_kmph=float(rules.get("parked_speed_threshold_kmph", 3.0)),
                lane_zones=lane_zones,
                emergency_labels=set(rules.get("emergency_labels", ["ambulance", "fire truck", "police car"])),
            )
        )

    def analyze(self, detections: list[Detection], timestamp: float | None = None) -> dict[str, Any]:
        timestamp = timestamp or time.time()
        vehicles: list[dict[str, Any]] = []
        tags: set[str] = set()
        max_speed = 0.0

        for detection in detections:
            label = detection.label.lower()
            if label not in VEHICLE_LABELS and label != "person":
                continue
            track_id = detection.tracker_id or -1
            center = bbox_center(detection.bbox)
            speed = self._estimate_speed(track_id, center, timestamp)
            max_speed = max(max_speed, speed)
            vehicle_tags = self._classify_vehicle(detection, center, speed, timestamp)
            tags.update(vehicle_tags)
            vehicles.append(
                {
                    "track_id": track_id,
                    "label": detection.label,
                    "confidence": round(detection.confidence, 4),
                    "bbox": detection.bbox,
                    "center": center,
                    "speed_kmph": round(speed, 2),
                    "speed_limit_kmph": self.rules.speed_limit_kmph,
                    "tags": sorted(vehicle_tags),
                }
            )

        if vehicles:
            tags.add("vehicle_detection")
        return {
            "tags": sorted(tags),
            "vehicle_count": len([v for v in vehicles if v["label"].lower() in VEHICLE_LABELS]),
            "person_count": len([v for v in vehicles if v["label"].lower() == "person"]),
            "max_speed_kmph": round(max_speed, 2),
            "vehicles": vehicles,
        }

    def _estimate_speed(self, track_id: int, center: tuple[float, float], timestamp: float) -> float:
        if track_id < 0:
            return 0.0
        history = self.track_history[track_id]
        history.append((timestamp, center))
        if len(history) < 2:
            return 0.0
        # Use the last two samples for responsive live speed (not the full deque span).
        old_ts, old_center = history[-2]
        dt = max(1e-6, timestamp - old_ts)
        distance_px = ((center[0] - old_center[0]) ** 2 + (center[1] - old_center[1]) ** 2) ** 0.5
        meters = distance_px / max(1e-6, self.rules.pixels_per_meter)
        return meters / dt * 3.6

    def _classify_vehicle(self, detection: Detection, center: tuple[float, float], speed: float, timestamp: float) -> set[str]:
        tags: set[str] = set()
        label = detection.label.lower()
        track_id = detection.tracker_id or -1

        if label in self.rules.emergency_labels:
            tags.add("emergency_vehicle_prioritization")

        if label in VEHICLE_LABELS and speed > self.rules.speed_limit_kmph:
            tags.add("speed_limit_warning")

        if self._is_wrong_way(track_id):
            tags.add("wrong_way_detection")

        if self._is_lane_violation(center):
            tags.add("lane_violation_detection")

        if label in VEHICLE_LABELS and speed <= self.rules.parked_speed_threshold_kmph:
            started = self.stationary_since.setdefault(track_id, timestamp)
            if timestamp - started >= self.rules.illegal_parking_seconds:
                tags.add("illegal_parking_detection")
        else:
            self.stationary_since.pop(track_id, None)

        return tags

    def _is_wrong_way(self, track_id: int) -> bool:
        history = self.track_history.get(track_id)
        if not history or len(history) < 5:
            return False
        _, first = history[0]
        _, last = history[-1]
        dx = last[0] - first[0]
        dy = last[1] - first[1]
        displacement = (dx * dx + dy * dy) ** 0.5
        if displacement < self.rules.wrong_way_min_displacement_px:
            return False
        allowed_x, allowed_y = self.rules.allowed_direction
        dot = dx * allowed_x + dy * allowed_y
        return dot < 0

    def _is_lane_violation(self, center: tuple[float, float]) -> bool:
        if not self.rules.lane_zones:
            return False
        return not any(point_in_polygon(center, zone) for zone in self.rules.lane_zones)
