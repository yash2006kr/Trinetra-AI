"""Motion-triggered event recorder with pre-event buffering."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from time import time
from typing import Any
from uuid import uuid4

import cv2
import numpy as np

from shared_core.recording_engine.circular_buffer import FrameCircularBuffer
from shared_core.utils.logging import setup_logger


@dataclass(slots=True)
class RecorderConfig:
    output_dir: str = "data/recordings"
    snapshot_dir: str = "data/snapshots"
    pre_event_seconds: float = 4.0
    stop_timeout_seconds: float = 8.0
    target_fps: float = 12.0
    inactive_fps: float = 2.0
    codec: str = "mp4v"
    container: str = "mp4"
    min_event_score: float = 0.18
    snapshot_score_threshold: float = 0.08
    minor_event_snapshot_cooldown: float = 30.0
    max_clip_seconds: float = 300.0


@dataclass(slots=True)
class RecordingEvent:
    event_id: str
    camera_id: str
    module_name: str
    clip_path: Path
    metadata_path: Path
    start_ts: float
    last_motion_ts: float
    score: float
    tags: set[str] = field(default_factory=set)
    frame_count: int = 0


@dataclass(slots=True)
class RecordingResult:
    started: RecordingEvent | None = None
    finished: RecordingEvent | None = None
    snapshot_path: Path | None = None


class MotionEventRecorder:
    """Stateful recorder that writes clips only around meaningful events."""

    def __init__(self, camera_id: str, module_name: str, frame_size: tuple[int, int], config: RecorderConfig | None = None) -> None:
        self.camera_id = camera_id
        self.module_name = module_name
        self.frame_size = frame_size
        self.config = config or RecorderConfig()
        self.output_dir = Path(self.config.output_dir) / module_name / camera_id
        self.snapshot_dir = Path(self.config.snapshot_dir) / module_name / camera_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.prebuffer = FrameCircularBuffer(self.config.pre_event_seconds, self.config.target_fps)
        self.active_event: RecordingEvent | None = None
        self._writer: cv2.VideoWriter | None = None
        self._last_snapshot_ts = 0.0
        self.logger = setup_logger(f"recorder.{module_name}.{camera_id}", "logs")

    def process(
        self,
        frame: np.ndarray,
        timestamp: float,
        motion_active: bool,
        importance: float,
        tags: list[str] | set[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RecordingResult:
        """Update recorder state for a frame and return lifecycle changes."""

        tags_set = set(tags or [])
        result = RecordingResult()
        self.prebuffer.append(frame, timestamp)

        if self.active_event is None:
            if motion_active and importance >= self.config.min_event_score:
                result.started = self._start_event(frame, timestamp, importance, tags_set, metadata or {})
            elif motion_active and importance >= self.config.snapshot_score_threshold:
                result.snapshot_path = self._save_minor_snapshot(frame, timestamp, importance, tags_set, metadata or {})
            return result

        event = self.active_event
        event.score = max(event.score, importance)
        event.tags.update(tags_set)
        if motion_active:
            event.last_motion_ts = timestamp
        self._write_frame(frame)

        age = timestamp - event.start_ts
        idle_seconds = timestamp - event.last_motion_ts
        if idle_seconds >= self.config.stop_timeout_seconds or age >= self.config.max_clip_seconds:
            result.finished = self._finish_event(timestamp, metadata or {})
        return result

    def _start_event(
        self,
        frame: np.ndarray,
        timestamp: float,
        importance: float,
        tags: set[str],
        metadata: dict[str, Any],
    ) -> RecordingEvent:
        event_id = uuid4().hex
        clip_path = self.output_dir / f"{event_id}.{self.config.container}"
        metadata_path = self.output_dir / f"{event_id}.json"
        fourcc = cv2.VideoWriter_fourcc(*self.config.codec[:4])
        height, width = frame.shape[:2]
        self.frame_size = (width, height)
        self._writer = cv2.VideoWriter(str(clip_path), fourcc, self.config.target_fps, self.frame_size)
        if not self._writer.isOpened():
            fallback = cv2.VideoWriter_fourcc(*"mp4v")
            self._writer = cv2.VideoWriter(str(clip_path), fallback, self.config.target_fps, self.frame_size)
        self.active_event = RecordingEvent(
            event_id=event_id,
            camera_id=self.camera_id,
            module_name=self.module_name,
            clip_path=clip_path,
            metadata_path=metadata_path,
            start_ts=timestamp,
            last_motion_ts=timestamp,
            score=importance,
            tags=tags,
        )
        for buffered in self.prebuffer.snapshot():
            self._write_frame(buffered.frame)
        self._write_frame(frame)
        self.logger.info("Started event %s score=%.3f tags=%s", event_id, importance, sorted(tags))
        self._write_metadata(self.active_event, timestamp, "started", metadata)
        return self.active_event

    def _write_frame(self, frame: np.ndarray) -> None:
        if not self._writer or not self.active_event:
            return
        if (frame.shape[1], frame.shape[0]) != self.frame_size:
            frame = cv2.resize(frame, self.frame_size)
        self._writer.write(frame)
        self.active_event.frame_count += 1

    def _finish_event(self, timestamp: float, metadata: dict[str, Any]) -> RecordingEvent:
        assert self.active_event is not None
        event = self.active_event
        if self._writer:
            self._writer.release()
        self._writer = None
        self.active_event = None
        self._write_metadata(event, timestamp, "finished", metadata)
        self.logger.info("Finished event %s frames=%s score=%.3f", event.event_id, event.frame_count, event.score)
        return event

    def _save_minor_snapshot(
        self,
        frame: np.ndarray,
        timestamp: float,
        importance: float,
        tags: set[str],
        metadata: dict[str, Any],
    ) -> Path | None:
        if timestamp - self._last_snapshot_ts < self.config.minor_event_snapshot_cooldown:
            return None
        self._last_snapshot_ts = timestamp
        snapshot_path = self.snapshot_dir / f"{int(timestamp)}_{uuid4().hex[:8]}.jpg"
        cv2.imwrite(str(snapshot_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
        sidecar = snapshot_path.with_suffix(".json")
        sidecar.write_text(
            json.dumps(
                {
                    "camera_id": self.camera_id,
                    "module": self.module_name,
                    "timestamp": timestamp,
                    "importance": importance,
                    "tags": sorted(tags),
                    "metadata": metadata,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return snapshot_path

    def _write_metadata(self, event: RecordingEvent, timestamp: float, state: str, metadata: dict[str, Any]) -> None:
        payload = {
            "event_id": event.event_id,
            "camera_id": event.camera_id,
            "module": event.module_name,
            "clip_path": str(event.clip_path),
            "start_ts": event.start_ts,
            "updated_ts": timestamp,
            "duration_seconds": round(timestamp - event.start_ts, 3),
            "state": state,
            "score": event.score,
            "tags": sorted(event.tags),
            "frame_count": event.frame_count,
            "metadata": metadata,
        }
        event.metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def close(self) -> RecordingEvent | None:
        if self.active_event:
            return self._finish_event(time(), {"reason": "recorder_closed"})
        return None
