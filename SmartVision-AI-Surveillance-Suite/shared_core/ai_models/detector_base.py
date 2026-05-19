"""Shared detector interfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Detection:
    bbox: tuple[float, float, float, float]
    confidence: float
    class_id: int
    label: str
    tracker_id: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ObjectDetector:
    def detect(self, frame: Any) -> list[Detection]:
        raise NotImplementedError
