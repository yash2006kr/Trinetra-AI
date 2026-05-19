"""Thread-safe multi-camera manager."""

from __future__ import annotations

from threading import RLock

import numpy as np

from shared_core.stream_manager.camera import CameraConfig, CameraHealth, ThreadedCamera


class CameraManager:
    def __init__(self) -> None:
        self._cameras: dict[str, ThreadedCamera] = {}
        self._lock = RLock()
        self._active_camera_id: str | None = None

    def add_camera(self, config: CameraConfig, start: bool = True) -> ThreadedCamera:
        with self._lock:
            camera = ThreadedCamera(config)
            old = self._cameras.get(config.camera_id)
            if old:
                old.stop()
            self._cameras[config.camera_id] = camera
            if start and config.enabled:
                camera.start()
                self._active_camera_id = config.camera_id
            return camera

    def activate_only(self, camera_id: str) -> bool:
        """Stop every camera and start only the selected device (avoids dual-webcam conflicts)."""

        with self._lock:
            camera = self._cameras.get(camera_id)
            if not camera:
                return False
            for other_id, other in self._cameras.items():
                if other_id != camera_id:
                    other.stop()
            camera.start()
            self._active_camera_id = camera_id
        return True

    def active_camera_id(self) -> str | None:
        with self._lock:
            return self._active_camera_id

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

    def pause(self, camera_id: str) -> bool:
        """Stop capture and release the camera device."""

        with self._lock:
            camera = self._cameras.get(camera_id)
        if not camera:
            return False
        camera.stop()
        return True

    def resume(self, camera_id: str) -> bool:
        """Start capture again after pause."""

        with self._lock:
            camera = self._cameras.get(camera_id)
        if not camera:
            return False
        camera.start()
        return True

    def is_running(self, camera_id: str) -> bool:
        with self._lock:
            camera = self._cameras.get(camera_id)
        if not camera:
            return False
        health = camera.health()
        return health.running and health.connected

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
