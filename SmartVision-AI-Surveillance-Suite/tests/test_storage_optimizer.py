from __future__ import annotations

from shared_core.recording_engine.storage_optimizer import AdaptiveCompressionPolicy, FrameScheduler


def test_frame_scheduler_uses_lower_inactive_rate() -> None:
    scheduler = FrameScheduler(active_fps=10, inactive_fps=1)
    assert scheduler.should_emit(0.0, motion_active=False)
    assert not scheduler.should_emit(0.5, motion_active=False)
    assert scheduler.should_emit(1.1, motion_active=False)


def test_adaptive_compression_policy() -> None:
    policy = AdaptiveCompressionPolicy()
    assert policy.crf_for_score(0.9) < policy.crf_for_score(0.1)
