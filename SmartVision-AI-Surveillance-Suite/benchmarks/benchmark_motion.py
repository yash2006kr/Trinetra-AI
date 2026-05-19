"""Micro-benchmark for the motion engine."""

from __future__ import annotations

import time

import numpy as np

from shared_core.motion_engine.motion_detector import MotionDetector


def main() -> None:
    detector = MotionDetector()
    frames = []
    for idx in range(300):
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame[100:180, idx % 1180 : idx % 1180 + 80] = 255
        frames.append(frame)

    start = time.perf_counter()
    active = 0
    for frame in frames:
        state = detector.process(frame)
        active += int(state.active)
    elapsed = time.perf_counter() - start
    print({"frames": len(frames), "active_frames": active, "fps": round(len(frames) / elapsed, 2)})


if __name__ == "__main__":
    main()
