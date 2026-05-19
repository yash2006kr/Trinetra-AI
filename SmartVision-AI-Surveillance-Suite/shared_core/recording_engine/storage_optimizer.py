"""Storage optimization policies used before recording decisions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class FrameScheduler:
    """Throttle frame processing differently for active and inactive scenes."""

    active_fps: float = 12.0
    inactive_fps: float = 2.0
    _last_emit_ts: float = field(default=float("-inf"), init=False)

    def should_emit(self, timestamp: float, motion_active: bool) -> bool:
        target_fps = self.active_fps if motion_active else self.inactive_fps
        min_interval = 1.0 / max(0.1, target_fps)
        if timestamp - self._last_emit_ts >= min_interval:
            self._last_emit_ts = timestamp
            return True
        return False


@dataclass(frozen=True, slots=True)
class AdaptiveCompressionPolicy:
    """Map event importance to ffmpeg CRF presets for post-compression."""

    high_importance_crf: int = 23
    normal_crf: int = 28
    low_importance_crf: int = 32

    def crf_for_score(self, score: float) -> int:
        if score >= 0.65:
            return self.high_importance_crf
        if score >= 0.25:
            return self.normal_crf
        return self.low_importance_crf
