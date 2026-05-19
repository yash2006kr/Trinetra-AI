"""Live vision overlays and inference helpers."""

from shared_core.vision.live_processor import LiveInferenceProcessor
from shared_core.vision.overlay import annotate_frame

__all__ = ["LiveInferenceProcessor", "annotate_frame"]
