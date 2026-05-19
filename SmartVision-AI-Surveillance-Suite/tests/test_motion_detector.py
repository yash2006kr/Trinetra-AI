from __future__ import annotations

import numpy as np

from shared_core.motion_engine.motion_detector import MotionConfig, MotionDetector


def test_motion_detector_detects_moving_region() -> None:
    detector = MotionDetector(MotionConfig(min_area=50, threshold=10))
    frame1 = np.zeros((120, 160, 3), dtype=np.uint8)
    frame2 = frame1.copy()
    frame2[40:70, 50:90] = 255

    detector.process(frame1, timestamp=1.0)
    state = detector.process(frame2, timestamp=2.0)

    assert state.active
    assert state.score > 0
    assert state.contour_boxes
