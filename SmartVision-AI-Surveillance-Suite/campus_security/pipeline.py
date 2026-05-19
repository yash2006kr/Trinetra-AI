"""Pipeline entrypoint for campus_security."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from shared_core.ai_models.detector_base import Detection
from shared_core.module_runtime import DomainPipeline


class CampusSecurityPipeline(DomainPipeline):
    def __init__(self, config_path: str | Path | None = None) -> None:
        super().__init__("campus_security", config_path or Path(__file__).with_name("config.yaml"))

    def analyze_detections(self, detections: list[Detection], frame: Any, timestamp: float) -> tuple[list[str], dict[str, Any]]:
        target_labels = set(self.config.get("ai", {}).get("target_labels", []))
        labels = [d.label for d in detections if not target_labels or d.label in target_labels]
        tags = sorted(set(labels))
        return tags, {
            "object_count": len(labels),
            "labels": tags,
            "features": self.config.get("module", {}).get("features", []),
        }
