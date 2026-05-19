"""Reusable module service runtime."""

from __future__ import annotations

import signal
import time
from dataclasses import asdict
from dataclasses import dataclass, field
from pathlib import Path
from threading import Event
from typing import Any

from shared_core.alert_engine.alerts import AlertDispatcher
from shared_core.ai_models.detector_base import Detection
from shared_core.ai_models.yolo_detector import YOLODetector
from shared_core.database.repository import EventRepository
from shared_core.motion_engine.importance import importance_score
from shared_core.motion_engine.motion_detector import MotionConfig, MotionDetector
from shared_core.recording_engine.event_recorder import MotionEventRecorder, RecorderConfig
from shared_core.recording_engine.storage_optimizer import FrameScheduler
from shared_core.stream_manager.camera import CameraConfig
from shared_core.stream_manager.camera_manager import CameraManager
from shared_core.tracking_engine.tracker import TrackerFactory
from shared_core.utils.config import load_config
from shared_core.utils.logging import setup_logger


@dataclass(slots=True)
class DomainFeature:
    name: str
    enabled: bool = True
    priority: str = "medium"
    labels: list[str] = field(default_factory=list)


class DomainPipeline:
    """Generic independent pipeline used by starter domain modules."""

    def __init__(self, module_name: str, config_path: str | Path) -> None:
        self.module_name = module_name
        self.config_path = Path(config_path)
        self.config = load_config(self.config_path)
        self.logger = setup_logger(module_name, self.config_path.parent / "logs")
        ai_config = self.config.get("ai", {})
        self.detector = YOLODetector(
            model_path=ai_config.get("model_path", "yolo11n.pt"),
            confidence=float(ai_config.get("confidence", 0.35)),
            image_size=int(ai_config.get("image_size", 640)),
            device=ai_config.get("device", "auto"),
            use_half_precision=bool(ai_config.get("use_half_precision", True)),
        )
        self.motion_config = MotionConfig(**self.config.get("motion", {}))
        self.tracker = TrackerFactory.create(self.config.get("tracking", {}).get("type", "bytetrack"))
        self.camera_manager = CameraManager()
        self.alerts = AlertDispatcher()
        self.repository = EventRepository.from_config(self.config)
        self.stop_event = Event()

    def load_cameras(self) -> None:
        for raw in self.config.get("cameras", []):
            self.camera_manager.add_camera(CameraConfig(**raw), start=True)
            self.repository.upsert_camera(
                camera_id=raw["camera_id"],
                source=str(raw["source"]),
                module=self.module_name,
                name=raw.get("name"),
                metadata=raw.get("metadata", {}),
            )

    def analyze_detections(self, detections: list[Detection], frame: Any, timestamp: float) -> tuple[list[str], dict[str, Any]]:
        labels = sorted({d.label for d in detections})
        return labels, {"detections": [asdict(d) for d in detections]}

    def run(self) -> None:
        self.load_cameras()
        recorders: dict[str, MotionEventRecorder] = {}
        motion_detectors: dict[str, MotionDetector] = {}
        frame_schedulers: dict[str, FrameScheduler] = {}
        recording_config = RecorderConfig(**self.config.get("recording", {}))

        def handle_signal(*_: Any) -> None:
            self.stop_event.set()

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)
        self.logger.info("Started %s pipeline", self.module_name)

        while not self.stop_event.is_set():
            for camera_id, (_, frame, timestamp) in self.camera_manager.snapshot_all().items():
                if frame is None:
                    continue
                timestamp = timestamp or time.time()
                motion_detector = motion_detectors.setdefault(camera_id, MotionDetector(self.motion_config))
                scheduler = frame_schedulers.setdefault(
                    camera_id,
                    FrameScheduler(active_fps=recording_config.target_fps, inactive_fps=recording_config.inactive_fps),
                )
                if camera_id not in recorders:
                    h, w = frame.shape[:2]
                    recorders[camera_id] = MotionEventRecorder(
                        camera_id=camera_id,
                        module_name=self.module_name,
                        frame_size=(w, h),
                        config=recording_config,
                    )
                motion = motion_detector.process(frame, timestamp)
                if not scheduler.should_emit(timestamp, motion.active):
                    continue
                detections = self.tracker.update(self.detector.detect(frame)) if motion.active else []
                try:
                    tags, metadata = self.analyze_detections(detections, frame, timestamp, camera_id)  # type: ignore[misc]
                except TypeError as exc:
                    if "positional" not in str(exc) and "argument" not in str(exc):
                        raise
                    tags, metadata = self.analyze_detections(detections, frame, timestamp)
                score = importance_score(motion, detections, self.config.get("importance", {}).get("class_weights"))
                result = recorders[camera_id].process(frame, timestamp, motion.active, score, tags, metadata)
                if result.finished:
                    self.repository.create_event_from_recording(result.finished)
            time.sleep(0.005)

        for recorder in recorders.values():
            event = recorder.close()
            if event:
                self.repository.create_event_from_recording(event)
        self.camera_manager.stop_all()
