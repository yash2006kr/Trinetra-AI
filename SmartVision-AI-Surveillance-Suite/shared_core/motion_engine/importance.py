"""AI/event importance scoring for recording decisions."""

from __future__ import annotations

from collections.abc import Iterable

from shared_core.ai_models.detector_base import Detection
from shared_core.motion_engine.motion_detector import MotionState


DEFAULT_CLASS_WEIGHTS = {
    "person": 0.35,
    "car": 0.25,
    "truck": 0.30,
    "bus": 0.30,
    "motorcycle": 0.25,
    "bicycle": 0.20,
    "fire": 0.60,
    "smoke": 0.55,
    "weapon": 0.75,
}


def importance_score(
    motion: MotionState,
    detections: Iterable[Detection] = (),
    class_weights: dict[str, float] | None = None,
    base_motion_weight: float = 0.35,
) -> float:
    """Return a normalized 0..1 score used for recording and retention policy."""

    weights = class_weights or DEFAULT_CLASS_WEIGHTS
    score = min(0.45, motion.score * base_motion_weight * 3.0)
    for detection in detections:
        score += weights.get(detection.label.lower(), 0.12) * max(0.1, detection.confidence)
    if motion.scene_changed:
        score *= 0.4
    return round(min(1.0, score), 4)
