"""Create a tiny synthetic highway sample video for local smoke tests."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def main() -> None:
    out_dir = Path("sample_datasets")
    out_dir.mkdir(exist_ok=True)
    path = out_dir / "highway_demo.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 15, (640, 360))
    for idx in range(180):
        frame = np.zeros((360, 640, 3), dtype=np.uint8)
        frame[:] = (35, 38, 42)
        cv2.line(frame, (0, 210), (640, 210), (90, 90, 90), 4)
        cv2.line(frame, (0, 270), (640, 270), (120, 120, 120), 4)
        x = 20 + idx * 3
        cv2.rectangle(frame, (x, 215), (x + 70, 255), (20, 160, 230), -1)
        cv2.circle(frame, (x + 15, 255), 8, (10, 10, 10), -1)
        cv2.circle(frame, (x + 55, 255), 8, (10, 10, 10), -1)
        writer.write(frame)
    writer.release()
    print(path)


if __name__ == "__main__":
    main()
