"""YOLO adapter with graceful fallback when optional model packages are absent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from shared_core.ai_models.detector_base import Detection, ObjectDetector
from shared_core.utils.gpu import resolve_device
from shared_core.utils.logging import setup_logger


class YOLODetector(ObjectDetector):
    """Thin Ultralytics YOLO wrapper.

    Supports YOLOv8 and YOLOv11 weights through the ``ultralytics`` package. The
    model is loaded lazily so API-only processes can start without initializing
    GPU memory.
    """

    def __init__(
        self,
        model_path: str = "yolo11n.pt",
        confidence: float = 0.35,
        image_size: int = 640,
        device: str = "auto",
        use_half_precision: bool = True,
        labels: dict[int, str] | None = None,
        graceful: bool = True,
    ) -> None:
        self.model_path = model_path
        self.confidence = confidence
        self.image_size = image_size
        self.runtime = resolve_device(device, use_half_precision)
        self.labels = labels or {}
        self.graceful = graceful
        self._model: Any | None = None
        self.logger = setup_logger("shared_core.yolo", "logs")

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            from ultralytics import YOLO

            self._model = YOLO(str(Path(self.model_path)))
            self.logger.info("Loaded YOLO model %s on %s", self.model_path, self.runtime.device)
        except Exception as exc:
            if not self.graceful:
                raise
            self.logger.warning("YOLO unavailable; detector will return no objects: %s", exc)
            self._model = False

    def detect(self, frame: np.ndarray) -> list[Detection]:
        self._load()
        if not self._model:
            return []

        results = self._model.predict(
            frame,
            conf=self.confidence,
            imgsz=self.image_size,
            device=self.runtime.device,
            half=self.runtime.half_precision,
            verbose=False,
        )
        detections: list[Detection] = []
        for result in results:
            names = getattr(result, "names", {}) or {}
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            for box in boxes:
                xyxy = box.xyxy[0].detach().cpu().tolist()
                conf = float(box.conf[0].detach().cpu())
                class_id = int(box.cls[0].detach().cpu())
                label = self.labels.get(class_id) or names.get(class_id, str(class_id))
                detections.append(Detection(tuple(xyxy), conf, class_id, label))
        return detections
