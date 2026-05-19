"""Thread-safe OpenCV camera capture with reconnect support."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from os import name as os_name
from typing import Any

import cv2
import numpy as np

from shared_core.utils.logging import setup_logger


def normalize_source(source: str | int) -> str | int:
    if isinstance(source, str) and source.isdigit():
        return int(source)
    return source


@dataclass(slots=True)
class CameraConfig:
    camera_id: str
    source: str | int
    name: str | None = None
    enabled: bool = True
    width: int | None = None
    height: int | None = None
    fps: float = 15.0
    reconnect_seconds: float = 5.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CameraHealth:
    camera_id: str
    running: bool
    connected: bool
    last_frame_ts: float | None
    frames_read: int
    failures: int


class ThreadedCamera:
    """Owns a single ``cv2.VideoCapture`` in a background thread."""

    def __init__(self, config: CameraConfig) -> None:
        self.config = config
        self.logger = setup_logger(f"camera.{config.camera_id}", "logs")
        self._capture: cv2.VideoCapture | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.RLock()
        self._latest: np.ndarray | None = None
        self._latest_ts: float | None = None
        self._connected = False
        self._frames_read = 0
        self._failures = 0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._capture_loop, name=f"camera-{self.config.camera_id}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3.0)
        with self._lock:
            if self._capture:
                self._capture.release()
            self._capture = None
            self._connected = False

    def read(self) -> tuple[bool, np.ndarray | None, float | None]:
        with self._lock:
            if self._latest is None:
                return False, None, None
            return True, self._latest.copy(), self._latest_ts

    def health(self) -> CameraHealth:
        with self._lock:
            return CameraHealth(
                camera_id=self.config.camera_id,
                running=bool(self._thread and self._thread.is_alive()),
                connected=self._connected,
                last_frame_ts=self._latest_ts,
                frames_read=self._frames_read,
                failures=self._failures,
            )

    def _open_capture(self) -> cv2.VideoCapture:
        source = normalize_source(self.config.source)
        if isinstance(source, int) and os_name == "nt":
            capture = cv2.VideoCapture(source, cv2.CAP_DSHOW)
        else:
            capture = cv2.VideoCapture(source)
        if self.config.width:
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
        if self.config.height:
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
        if self.config.fps:
            capture.set(cv2.CAP_PROP_FPS, self.config.fps)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return capture

    def _capture_loop(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                if self._capture is None or not self._capture.isOpened():
                    self._capture = self._open_capture()
                capture = self._capture

            if not capture or not capture.isOpened():
                with self._lock:
                    self._connected = False
                    self._failures += 1
                time.sleep(self.config.reconnect_seconds)
                continue

            ok, frame = capture.read()
            if not ok or frame is None:
                with self._lock:
                    self._connected = False
                    self._failures += 1
                    capture.release()
                    self._capture = None
                time.sleep(self.config.reconnect_seconds)
                continue

            now = time.time()
            with self._lock:
                self._latest = frame
                self._latest_ts = now
                self._connected = True
                self._frames_read += 1
            time.sleep(max(0.0, 1.0 / max(self.config.fps, 1.0) - 0.001))
