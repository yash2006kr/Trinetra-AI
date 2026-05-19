from __future__ import annotations

import numpy as np

from shared_core.recording_engine.event_recorder import MotionEventRecorder, RecorderConfig


def test_recorder_starts_and_stops_event(tmp_path) -> None:
    frame = np.zeros((80, 120, 3), dtype=np.uint8)
    recorder = MotionEventRecorder(
        "cam1",
        "test_module",
        (120, 80),
        RecorderConfig(
            output_dir=str(tmp_path / "clips"),
            snapshot_dir=str(tmp_path / "snapshots"),
            pre_event_seconds=1,
            stop_timeout_seconds=0.2,
            target_fps=5,
            min_event_score=0.1,
        ),
    )

    assert recorder.process(frame, 1.0, False, 0.0).started is None
    started = recorder.process(frame, 1.1, True, 0.5, ["motion"]).started
    assert started is not None
    finished = recorder.process(frame, 1.5, False, 0.0).finished
    assert finished is not None
    assert finished.clip_path.exists()
    assert finished.metadata_path.exists()
