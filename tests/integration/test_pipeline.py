from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from traffic_analytics.config import load_config
from traffic_analytics.models import BoundingBox, Detection, TrackObservation
from traffic_analytics.pipeline import PipelineMode, PipelineState, _safe_output_fps, process_frame

ROOT = Path(__file__).parents[2]


def _detection(y2: float, confidence: float = 0.9) -> Detection:
    return Detection(2, "car", confidence, BoundingBox(40.0, y2 - 20.0, 60.0, y2))


class FakeAdapter:
    def __init__(self, y_positions: tuple[float, ...] = (50.0, 70.0)) -> None:
        self._positions = y_positions
        self.detect_calls = 0
        self.track_calls = 0

    def detect(self, frame: np.ndarray) -> tuple[Detection, ...]:
        self.detect_calls += 1
        return (_detection(50.0),)

    def track(self, frame: np.ndarray) -> tuple[TrackObservation, ...]:
        y2 = self._positions[self.track_calls]
        self.track_calls += 1
        return (TrackObservation(7, _detection(y2), age=3 + self.track_calls),)


def _config():
    config = load_config(ROOT / "configs" / "default.yaml")
    return config.model_copy(
        update={"video": config.video.model_copy(update={"show_preview": False})}
    )


def test_detect_mode_does_not_invoke_tracker_or_counter() -> None:
    adapter = FakeAdapter()
    original = PipelineState()

    result, next_state = process_frame(
        np.zeros((100, 100, 3), dtype=np.uint8),
        frame_index=0,
        mode=PipelineMode.DETECT,
        config=_config(),
        adapter=adapter,
        state=original,
    )

    assert adapter.detect_calls == 1
    assert adapter.track_calls == 0
    assert len(result.detections) == 1
    assert result.tracks == ()
    assert result.events == ()
    assert next_state == original
    assert result.annotated_frame is not result.raw_frame


def test_analyze_mode_tracks_trajectory_and_emits_one_crossing() -> None:
    adapter = FakeAdapter()
    state = PipelineState()

    first, state = process_frame(
        np.zeros((100, 100, 3), dtype=np.uint8),
        frame_index=0,
        mode=PipelineMode.ANALYZE,
        config=_config(),
        adapter=adapter,
        state=state,
    )
    second, state = process_frame(
        np.zeros((100, 100, 3), dtype=np.uint8),
        frame_index=1,
        mode=PipelineMode.ANALYZE,
        config=_config(),
        adapter=adapter,
        state=state,
    )

    assert first.events == ()
    assert len(second.events) == 1
    assert second.events[0].track_id == 7
    assert second.events[0].direction.value == "IN"
    assert len(state.counter.events) == 1


def test_track_mode_builds_trajectory_without_counting() -> None:
    adapter = FakeAdapter((50.0,))

    result, state = process_frame(
        np.zeros((100, 100, 3), dtype=np.uint8),
        frame_index=0,
        mode=PipelineMode.TRACK,
        config=_config(),
        adapter=adapter,
        state=PipelineState(),
    )

    assert len(result.tracks) == 1
    assert result.events == ()
    assert state.counter.events == ()


def test_pipeline_rejects_invalid_frame_shape() -> None:
    with pytest.raises(ValueError, match="frame"):
        process_frame(
            np.zeros((10, 10), dtype=np.uint8),
            frame_index=0,
            mode=PipelineMode.DETECT,
            config=_config(),
            adapter=FakeAdapter(),
            state=PipelineState(),
        )


@pytest.mark.parametrize(
    ("reported_fps", "expected_fps"),
    [
        (24.0, 24.0),
        (240.0, 240.0),
        (0.0, 30.0),
        (-1.0, 30.0),
        (1_000.0, 30.0),
        (float("nan"), 30.0),
    ],
)
def test_pipeline_uses_safe_fallback_for_implausible_source_fps(
    reported_fps: float, expected_fps: float
) -> None:
    assert _safe_output_fps(reported_fps) == expected_fps
