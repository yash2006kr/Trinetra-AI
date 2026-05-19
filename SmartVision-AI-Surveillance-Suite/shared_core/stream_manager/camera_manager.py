"""Thread-safe multi-camera manager."""

from __future__ import annotations

from threading import RLock

import numpy as np

from shared_core.stream_manager.camera import CameraConfig, CameraHealth, ThreadedCamera


class CameraManager:
    def __init__(self) -> None:
        self._cameras: dict[str, ThreadedCamera] = {}
        self._lock = RLock()

    def add_camera(self, config: CameraConfig, start: bool = True) -> ThreadedCamera:
        with self._lock:
            camera = ThreadedCamera(config)
            old = self._cameras.get(config.camera_id)
            if old:
                old.stop()
            self._cameras[config.camera_id] = camera
            if start and config.enabled:
                camera.start()
            return camera

    def remove_camera(self, camera_id: str) -> None:
        with self._lock:
            camera = self._cameras.pop(camera_id, None)
        if camera:
            camera.stop()

    def start_all(self) -> None:
        with self._lock:
            cameras = list(self._cameras.values())
        for camera in cameras:
            camera.start()

    def stop_all(self) -> None:
        with self._lock:
            cameras = list(self._cameras.values())
        for camera in cameras:
            camera.stop()

    def read(self, camera_id: str) -> tuple[bool, np.ndarray | None, float | None]:
        with self._lock:
            camera = self._cameras.get(camera_id)
        if not camera:
            return False, None, None
        return camera.read()

    def snapshot_all(self) -> dict[str, tuple[bool, np.ndarray | None, float | None]]:
        with self._lock:
            items = list(self._cameras.items())
        return {camera_id: camera.read() for camera_id, camera in items}

    def health(self) -> list[CameraHealth]:
        with self._lock:
            cameras = list(self._cameras.values())
        return [camera.health() for camera in cameras]
