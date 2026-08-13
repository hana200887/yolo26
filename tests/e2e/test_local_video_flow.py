from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytest

import traffic_analytics.pipeline as pipeline
from traffic_analytics.config import load_config
from traffic_analytics.evaluation import load_events_csv
from traffic_analytics.models import BoundingBox, Detection, TrackObservation
from traffic_analytics.pipeline import PipelineMode, run_video

ROOT = Path(__file__).parents[2]


class CrossingAdapter:
    def __init__(self) -> None:
        self._positions = (50.0, 55.0, 65.0, 70.0)
        self._index = 0

    def detect(self, frame: np.ndarray[Any, Any]) -> tuple[Detection, ...]:
        raise AssertionError("analyze mode must not call detect")

    def track(self, frame: np.ndarray[Any, Any]) -> tuple[TrackObservation, ...]:
        y2 = self._positions[self._index]
        self._index += 1
        detection = Detection(2, "car", 0.9, BoundingBox(40.0, y2 - 20.0, 60.0, y2))
        return (TrackObservation(1, detection, age=self._index + 2),)


class FailingAdapter(CrossingAdapter):
    def track(self, frame: np.ndarray[Any, Any]) -> tuple[TrackObservation, ...]:
        if self._index == 1:
            raise RuntimeError("intentional model failure")
        return super().track(frame)


def _write_video(path: Path) -> None:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"MJPG"),  # type: ignore[attr-defined]
        10.0,
        (100, 100),
    )
    assert writer.isOpened()
    try:
        for shade in (0, 20, 40, 60):
            writer.write(np.full((100, 100, 3), shade, dtype=np.uint8))
    finally:
        writer.release()


def test_local_video_to_annotated_video_events_and_summary(tmp_path: Path) -> None:
    source = tmp_path / "input.avi"
    output_dir = tmp_path / "outputs"
    _write_video(source)
    config = load_config(ROOT / "configs" / "default.yaml")
    config = config.model_copy(
        update={
            "video": config.video.model_copy(
                update={"output_dir": output_dir, "show_preview": False, "save_output": True}
            )
        }
    )

    summary = run_video(
        source,
        mode=PipelineMode.ANALYZE,
        config=config,
        adapter=CrossingAdapter(),
    )

    assert summary.frames == 4
    assert summary.crossing_events == 1
    assert summary.video_output is not None
    assert summary.video_output.name == "input-analyze.mp4"
    assert summary.video_output.stat().st_size > 0
    output_capture = cv2.VideoCapture(str(summary.video_output))
    try:
        assert output_capture.isOpened()
        decoded_frames = 0
        while output_capture.read()[0]:
            decoded_frames += 1
        assert decoded_frames == 4
    finally:
        output_capture.release()
    assert summary.events_output is not None
    assert load_events_csv(summary.events_output)[0].track_id == 1
    summary_path = summary.video_output.with_suffix(".summary.json")
    assert json.loads(summary_path.read_text(encoding="utf-8"))["crossing_events"] == 1
    assert not list(output_dir.glob("*.tmp.*"))


def test_second_run_uses_a_distinct_output_base(tmp_path: Path) -> None:
    source = tmp_path / "input.v1.avi"
    output_dir = tmp_path / "outputs"
    _write_video(source)
    config = load_config(ROOT / "configs" / "default.yaml")
    config = config.model_copy(
        update={
            "video": config.video.model_copy(
                update={"output_dir": output_dir, "show_preview": False, "save_output": True}
            )
        }
    )

    first = run_video(source, mode=PipelineMode.ANALYZE, config=config, adapter=CrossingAdapter())
    second = run_video(source, mode=PipelineMode.ANALYZE, config=config, adapter=CrossingAdapter())

    assert first.video_output is not None
    assert second.video_output is not None
    assert first.video_output.name == "input.v1-analyze.mp4"
    assert second.video_output.name == "input.v1-analyze-1.mp4"
    assert not list(output_dir.glob("*.reservation"))


def test_failed_video_run_does_not_publish_partial_artifacts(tmp_path: Path) -> None:
    source = tmp_path / "input.avi"
    output_dir = tmp_path / "outputs"
    _write_video(source)
    config = load_config(ROOT / "configs" / "default.yaml")
    config = config.model_copy(
        update={
            "video": config.video.model_copy(
                update={"output_dir": output_dir, "show_preview": False, "save_output": True}
            )
        }
    )

    with pytest.raises(RuntimeError, match="intentional model failure"):
        run_video(
            source,
            mode=PipelineMode.ANALYZE,
            config=config,
            adapter=FailingAdapter(),
        )

    assert output_dir.is_dir()
    assert list(output_dir.iterdir()) == []


def test_late_event_write_failure_does_not_publish_video(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "input.avi"
    output_dir = tmp_path / "outputs"
    _write_video(source)
    config = load_config(ROOT / "configs" / "default.yaml")
    config = config.model_copy(
        update={
            "video": config.video.model_copy(
                update={"output_dir": output_dir, "show_preview": False, "save_output": True}
            )
        }
    )

    def fail_event_write(path: Path, events: tuple[object, ...]) -> None:
        raise OSError("intentional event write failure")

    monkeypatch.setattr(pipeline, "_write_events", fail_event_write)

    with pytest.raises(OSError, match="intentional event write failure"):
        run_video(
            source,
            mode=PipelineMode.ANALYZE,
            config=config,
            adapter=CrossingAdapter(),
        )

    assert output_dir.is_dir()
    assert list(output_dir.iterdir()) == []


def test_publish_failure_rolls_back_an_already_published_video(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "input.avi"
    output_dir = tmp_path / "outputs"
    _write_video(source)
    config = load_config(ROOT / "configs" / "default.yaml")
    config = config.model_copy(
        update={
            "video": config.video.model_copy(
                update={"output_dir": output_dir, "show_preview": False, "save_output": True}
            )
        }
    )
    publish = pipeline._publish_artifact
    attempts = 0

    def fail_second_publish(temporary_path: Path, final_path: Path) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 2:
            raise OSError("intentional publish failure")
        publish(temporary_path, final_path)

    monkeypatch.setattr(pipeline, "_publish_artifact", fail_second_publish)

    with pytest.raises(OSError, match="intentional publish failure"):
        run_video(
            source,
            mode=PipelineMode.ANALYZE,
            config=config,
            adapter=CrossingAdapter(),
        )

    assert output_dir.is_dir()
    assert list(output_dir.iterdir()) == []
