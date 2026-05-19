"""Tracker abstraction with a lightweight centroid fallback."""

from __future__ import annotations

from dataclasses import dataclass

from shared_core.ai_models.detector_base import Detection
from shared_core.utils.geometry import bbox_center


@dataclass(slots=True)
class Track:
    track_id: int
    detection: Detection
    age: int = 0
    missing: int = 0


class SimpleCentroidTracker:
    """Small dependency-free tracker for starter deployments and tests."""

    def __init__(self, max_distance: float = 80.0, max_missing: int = 15) -> None:
        self.max_distance = max_distance
        self.max_missing = max_missing
        self._next_id = 1
        self._tracks: dict[int, Track] = {}

    def update(self, detections: list[Detection]) -> list[Detection]:
        unmatched = set(range(len(detections)))
        for track_id, track in list(self._tracks.items()):
            best_idx = None
            best_distance = float("inf")
            tx, ty = bbox_center(track.detection.bbox)
            for idx in unmatched:
                dx, dy = bbox_center(detections[idx].bbox)
                distance = ((tx - dx) ** 2 + (ty - dy) ** 2) ** 0.5
                if distance < best_distance:
                    best_idx = idx
                    best_distance = distance
            if best_idx is not None and best_distance <= self.max_distance:
                detection = detections[best_idx]
                detection.tracker_id = track_id
                track.detection = detection
                track.age += 1
                track.missing = 0
                unmatched.remove(best_idx)
            else:
                track.missing += 1
                if track.missing > self.max_missing:
                    del self._tracks[track_id]

        for idx in unmatched:
            detection = detections[idx]
            detection.tracker_id = self._next_id
            self._tracks[self._next_id] = Track(self._next_id, detection)
            self._next_id += 1
        return detections


class TrackerFactory:
    @staticmethod
    def create(kind: str = "bytetrack") -> SimpleCentroidTracker:
        # The abstraction leaves room for DeepSORT/ByteTrack adapters while
        # keeping the starter project runnable without heavyweight trackers.
        return SimpleCentroidTracker()
