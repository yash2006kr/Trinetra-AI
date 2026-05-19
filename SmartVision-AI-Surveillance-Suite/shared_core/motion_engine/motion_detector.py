"""Motion detection using frame differencing and background subtraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import time

import cv2
import numpy as np


@dataclass(slots=True)
class MotionConfig:
    min_area: int = 900
    threshold: int = 25
    blur_kernel: int = 5
    history: int = 500
    var_threshold: float = 16.0
    detect_shadows: bool = True
    scene_change_threshold: float = 0.35


@dataclass(slots=True)
class MotionState:
    active: bool
    score: float
    changed_pixels_ratio: float
    contour_boxes: list[tuple[int, int, int, int]] = field(default_factory=list)
    scene_changed: bool = False
    timestamp: float = field(default_factory=time)


class MotionDetector:
    """Combines frame differencing with MOG2 background subtraction.

    The detector keeps static scenes quiet, marks hard scene cuts separately, and
    returns a normalized score that downstream recorders can use for storage
    decisions.
    """

    def __init__(self, config: MotionConfig | None = None) -> None:
        self.config = config or MotionConfig()
        self._previous_gray: np.ndarray | None = None
        self._subtractor = cv2.createBackgroundSubtractorMOG2(
            history=self.config.history,
            varThreshold=self.config.var_threshold,
            detectShadows=self.config.detect_shadows,
        )

    def process(self, frame: np.ndarray, timestamp: float | None = None) -> MotionState:
        timestamp = timestamp or time()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur_size = self.config.blur_kernel if self.config.blur_kernel % 2 == 1 else self.config.blur_kernel + 1
        gray = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)

        fg_mask = self._subtractor.apply(gray)
        _, fg_mask = cv2.threshold(fg_mask, self.config.threshold, 255, cv2.THRESH_BINARY)

        if self._previous_gray is None:
            self._previous_gray = gray
            return MotionState(active=False, score=0.0, changed_pixels_ratio=0.0, timestamp=timestamp)

        frame_delta = cv2.absdiff(self._previous_gray, gray)
        _, diff_mask = cv2.threshold(frame_delta, self.config.threshold, 255, cv2.THRESH_BINARY)
        combined = cv2.bitwise_or(fg_mask, diff_mask)
        combined = cv2.dilate(combined, None, iterations=2)

        contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contour_boxes: list[tuple[int, int, int, int]] = []
        moving_area = 0
        for contour in contours:
            area = int(cv2.contourArea(contour))
            if area < self.config.min_area:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            contour_boxes.append((x, y, w, h))
            moving_area += area

        changed_ratio = float(np.count_nonzero(combined)) / float(combined.size)
        scene_changed = changed_ratio >= self.config.scene_change_threshold
        score = min(1.0, moving_area / float(frame.shape[0] * frame.shape[1]))
        active = bool(contour_boxes) and not scene_changed
        self._previous_gray = gray
        return MotionState(active=active, score=score, changed_pixels_ratio=changed_ratio, contour_boxes=contour_boxes, scene_changed=scene_changed, timestamp=timestamp)
