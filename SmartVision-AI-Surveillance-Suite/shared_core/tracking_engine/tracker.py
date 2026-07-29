"""Tracker abstraction with ByteTrack support and a lightweight fallback."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from shared_core.ai_models.detector_base import Detection
from shared_core.utils.geometry import bbox_center, bbox_diagonal, bbox_iou


@dataclass(slots=True)
class Track:
    track_id: int
    detection: Detection
    age: int = 0
    missing: int = 0
    hits: int = 1


class DetectionTracker(Protocol):
    def update(self, detections: list[Detection]) -> list[Detection]:
        ...


class SimpleCentroidTracker:
    """Dependency-free tracker using class-aware IoU and centroid matching."""

    def __init__(self, max_distance: float = 120.0, max_missing: int = 20, min_iou: float = 0.05) -> None:
        self.max_distance = max_distance
        self.max_missing = max_missing
        self.min_iou = min_iou
        self._next_id = 1
        self._tracks: dict[int, Track] = {}

    def update(self, detections: list[Detection]) -> list[Detection]:
        if not detections:
            for track_id, track in list(self._tracks.items()):
                track.missing += 1
                if track.missing > self.max_missing:
                    del self._tracks[track_id]
            return detections

        for detection in detections:
            detection.tracker_id = None

        candidates: list[tuple[float, int, int]] = []
        unmatched = set(range(len(detections)))
        unmatched_tracks = set(self._tracks)

        for track_id, track in self._tracks.items():
            tx, ty = bbox_center(track.detection.bbox)
            track_diag = bbox_diagonal(track.detection.bbox)
            for idx in unmatched:
                if track.detection.label.lower() != detections[idx].label.lower():
                    continue
                dx, dy = bbox_center(detections[idx].bbox)
                distance = ((tx - dx) ** 2 + (ty - dy) ** 2) ** 0.5
                det_diag = bbox_diagonal(detections[idx].bbox)
                dynamic_limit = max(self.max_distance, 0.75 * max(track_diag, det_diag))
                overlap = bbox_iou(track.detection.bbox, detections[idx].bbox)
                if distance > dynamic_limit and overlap < self.min_iou:
                    continue
                distance_score = max(0.0, 1.0 - distance / max(dynamic_limit, 1e-6))
                score = 0.65 * overlap + 0.35 * distance_score
                candidates.append((score, track_id, idx))

        for _, track_id, idx in sorted(candidates, reverse=True):
            if track_id not in unmatched_tracks or idx not in unmatched:
                continue
            detection = detections[idx]
            detection.tracker_id = track_id
            track = self._tracks[track_id]
            track.detection = detection
            track.age += 1
            track.hits += 1
            track.missing = 0
            unmatched_tracks.remove(track_id)
            unmatched.remove(idx)

        for track_id in list(unmatched_tracks):
            track = self._tracks[track_id]
            track.missing += 1
            if track.missing > self.max_missing:
                del self._tracks[track_id]

        for idx in unmatched:
            detection = detections[idx]
            detection.tracker_id = self._next_id
            self._tracks[self._next_id] = Track(self._next_id, detection)
            self._next_id += 1
        return detections


class ByteTrackTracker:
    """Adapter around supervision's ByteTrack implementation."""

    def __init__(
        self,
        track_activation_threshold: float = 0.25,
        minimum_matching_threshold: float = 0.75,
        lost_track_buffer: int = 30,
        frame_rate: int = 30,
    ) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import supervision as sv

            self._sv = sv
            self._tracker = sv.ByteTrack(
                track_activation_threshold=track_activation_threshold,
                minimum_matching_threshold=minimum_matching_threshold,
                lost_track_buffer=lost_track_buffer,
                frame_rate=frame_rate,
                minimum_consecutive_frames=1,
            )

    def update(self, detections: list[Detection]) -> list[Detection]:
        for detection in detections:
            detection.tracker_id = None

        xyxy = np.asarray([d.bbox for d in detections], dtype=np.float32).reshape((-1, 4))
        confidence = np.asarray([d.confidence for d in detections], dtype=np.float32)
        class_id = np.asarray([d.class_id for d in detections], dtype=np.int32)
        source_index = np.arange(len(detections), dtype=np.int32)
        sv_detections = self._sv.Detections(
            xyxy=xyxy,
            confidence=confidence,
            class_id=class_id,
            data={"source_index": source_index},
        )
        tracked = self._tracker.update_with_detections(sv_detections)
        result: list[Detection] = []
        tracked_indices = set()

        tracker_ids = tracked.tracker_id if tracked.tracker_id is not None else []
        for idx, track_id in zip(tracked.data.get("source_index", []), tracker_ids, strict=False):
            source_idx = int(idx)
            detections[source_idx].tracker_id = int(track_id)
            tracked_indices.add(source_idx)
            result.append(detections[source_idx])

        # Keep high-confidence one-frame detections visible even before the
        # tracker has accepted them; analytics will ignore speed for ID-less rows.
        for idx, detection in enumerate(detections):
            if idx not in tracked_indices and detection.confidence >= 0.5:
                result.append(detection)
        return result


class TrackerFactory:
    @staticmethod
    def create(kind: str = "bytetrack") -> DetectionTracker:
        normalized = kind.replace("-", "_").lower()
        if normalized in {"bytetrack", "byte_track", "supervision_bytetrack"}:
            try:
                return ByteTrackTracker()
            except Exception:
                pass
        return SimpleCentroidTracker()
