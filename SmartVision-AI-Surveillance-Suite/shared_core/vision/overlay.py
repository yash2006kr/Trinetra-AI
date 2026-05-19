"""OpenCV drawing helpers for live detection overlays."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

COLOR_OK = (60, 220, 60)
COLOR_VIOLATION = (36, 36, 220)
COLOR_WARNING = (0, 165, 255)
COLOR_INFO = (255, 220, 80)
COLOR_TEXT = (255, 255, 255)

SECURITY_MODULES = {
    "home_security",
    "campus_security",
    "smart_city_security",
    "industrial_safety",
    "railway_surveillance",
    "wildlife_monitoring",
}

VIOLATION_TAGS = {
    "speed_limit_warning",
    "wrong_way_detection",
    "lane_violation_detection",
    "illegal_parking_detection",
}

VEHICLE_LABELS = {"car", "truck", "bus", "motorcycle", "bicycle"}


def _draw_label(
    frame: np.ndarray,
    text: str,
    x: int,
    y: int,
    color: tuple[int, int, int],
    font_scale: float = 0.5,
) -> None:
    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 1
    (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    y = max(text_h + 6, y)
    cv2.rectangle(frame, (x, y - text_h - 6), (x + text_w + 8, y + baseline), color, -1)
    cv2.putText(frame, text, (x + 4, y - 4), font, font_scale, COLOR_TEXT, thickness, cv2.LINE_AA)


def _box_color(module: str, vehicle: dict[str, Any], speed_limit_kmph: float | None = None) -> tuple[int, int, int]:
    label = vehicle.get("label", "").lower()
    tags = set(vehicle.get("tags") or [])

    if module == "highway_surveillance" and label in VEHICLE_LABELS:
        limit = speed_limit_kmph if speed_limit_kmph is not None else vehicle.get("speed_limit_kmph", 80)
        speed = float(vehicle.get("speed_kmph") or 0)
        if tags & VIOLATION_TAGS or speed > limit:
            return COLOR_VIOLATION
        return COLOR_OK

    if tags & VIOLATION_TAGS:
        return COLOR_VIOLATION
    if module in SECURITY_MODULES and label == "person":
        return COLOR_VIOLATION
    if tags:
        return COLOR_WARNING
    return COLOR_OK


def _vehicle_label(vehicle: dict[str, Any], module: str) -> str:
    label = vehicle.get("label", "object")
    speed = vehicle.get("speed_kmph")
    if module == "highway_surveillance" and label.lower() in VEHICLE_LABELS and speed is not None:
        limit = float(vehicle.get("speed_limit_kmph") or 80)
        status = "OVER LIMIT" if float(speed) > limit else "OK"
        return f"{label} {speed:.0f} km/h [{status}]"
    conf = vehicle.get("confidence")
    if conf is not None:
        return f"{label} {conf * 100:.0f}%"
    return str(label)


def draw_module_hud(
    frame: np.ndarray,
    module: str,
    analysis: dict[str, Any],
    speed_limit_kmph: float | None = None,
) -> None:
    lines: list[str] = [module.replace("_", " ").title()]
    if module == "highway_surveillance":
        limit = speed_limit_kmph or analysis.get("speed_limit_kmph", 80)
        lines.append(f"Speed limit: {limit:.0f} km/h")
        lines.append(f"Vehicles: {analysis.get('vehicle_count', 0)}")
        lines.append(f"Max speed: {analysis.get('max_speed_kmph', 0):.0f} km/h")
        violations = sum(
            1
            for vehicle in analysis.get("vehicles", [])
            if set(vehicle.get("tags") or []) & VIOLATION_TAGS
        )
        if violations:
            lines.append(f"Warnings: {violations}")
    else:
        lines.append(f"Detections: {len(analysis.get('vehicles', []))}")
        alerts = analysis.get("alert_count", 0)
        if alerts:
            lines.append(f"Alerts: {alerts}")

    y = 28
    for line in lines:
        _draw_label(frame, line, 10, y, (40, 40, 40), font_scale=0.55)
        y += 26

    cv2.rectangle(frame, (8, frame.shape[0] - 34), (170, frame.shape[0] - 8), (30, 30, 30), -1)
    cv2.circle(frame, (22, frame.shape[0] - 21), 6, COLOR_OK, -1)
    cv2.putText(frame, "OK", (34, frame.shape[0] - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, COLOR_OK, 1, cv2.LINE_AA)
    cv2.circle(frame, (72, frame.shape[0] - 21), 6, COLOR_VIOLATION, -1)
    cv2.putText(frame, "Alert", (88, frame.shape[0] - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, COLOR_VIOLATION, 1, cv2.LINE_AA)


def annotate_frame(
    frame: np.ndarray,
    module: str,
    analysis: dict[str, Any],
    speed_limit_kmph: float | None = None,
) -> np.ndarray:
    """Draw bounding boxes and HUD on a copy of the frame."""

    output = frame.copy()
    for vehicle in analysis.get("vehicles", []):
        bbox = vehicle.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
        x1, y1, x2, y2 = (int(v) for v in bbox)
        color = _box_color(module, vehicle, speed_limit_kmph=speed_limit_kmph)
        thickness = 3 if color == COLOR_VIOLATION else 2
        cv2.rectangle(output, (x1, y1), (x2, y2), color, thickness)
        tags = vehicle.get("tags") or []
        label = _vehicle_label(vehicle, module)
        if tags:
            label = f"{label} | {tags[0].replace('_', ' ')}"
        _draw_label(output, label, x1, y1, color)

    draw_module_hud(output, module, analysis, speed_limit_kmph=speed_limit_kmph)
    return output
