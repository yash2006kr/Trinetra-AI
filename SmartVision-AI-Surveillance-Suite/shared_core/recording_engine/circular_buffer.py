"""Thread-safe frame pre-buffer for event recording."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Lock

import numpy as np


@dataclass(slots=True)
class BufferedFrame:
    frame: np.ndarray
    timestamp: float


class FrameCircularBuffer:
    def __init__(self, max_seconds: float, fps: float) -> None:
        self.maxlen = max(1, int(max_seconds * fps))
        self._frames: deque[BufferedFrame] = deque(maxlen=self.maxlen)
        self._lock = Lock()

    def append(self, frame: np.ndarray, timestamp: float) -> None:
        with self._lock:
            self._frames.append(BufferedFrame(frame.copy(), timestamp))

    def snapshot(self) -> list[BufferedFrame]:
        with self._lock:
            return list(self._frames)

    def clear(self) -> None:
        with self._lock:
            self._frames.clear()
