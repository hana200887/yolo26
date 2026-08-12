"""Shared detect, track, and analyze video pipeline."""

from __future__ import annotations

import csv
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from time import perf_counter
from typing import Protocol, cast
from uuid import uuid4

import cv2
import numpy as np
from numpy.typing import NDArray

from traffic_analytics.config import AppConfig
from traffic_analytics.counting import CounterState, update_counter
from traffic_analytics.evaluation import EVENT_FIELDS
from traffic_analytics.models import (
    CountEvent,
    CrossingDirection,
    Detection,
    Point,
    TrackedObject,
    TrackObservation,
    TrajectoryState,
)
from traffic_analytics.trajectory import update_trajectories
from traffic_analytics.visualization import render_frame

Frame = NDArray[np.uint8]
SUPPORTED_VIDEO_SUFFIXES = frozenset({".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm"})
OUTPUT_ARTIFACT_SUFFIXES = (".mp4", ".events.csv", ".summary.json")


class PipelineMode(StrEnum):
    """Supported depth levels of the shared pipeline."""

    DETECT = "detect"
    TRACK = "track"
    ANALYZE = "analyze"


class AnalyticsAdapter(Protocol):
    """Detector/tracker boundary required by the shared pipeline."""

    def detect(self, frame: Frame) -> tuple[Detection, ...]: ...

    def track(self, frame: Frame) -> tuple[TrackObservation, ...]: ...


@dataclass(frozen=True, slots=True)
class PipelineState:
    """Immutable project-owned temporal state."""

    trajectories: TrajectoryState = field(default_factory=TrajectoryState)
    counter: CounterState = field(default_factory=CounterState)


@dataclass(frozen=True, slots=True)
class FrameResult:
    """All outputs for one processed frame."""

    frame_index: int
    raw_frame: Frame
    annotated_frame: Frame
    detections: tuple[Detection, ...]
    tracks: tuple[TrackedObject, ...]
    events: tuple[CountEvent, ...]


@dataclass(frozen=True, slots=True)
class RunSummary:
    """Measured runtime summary for one completed video."""

    mode: PipelineMode
    source: Path
    frames: int
    detections: int
    tracked_objects: int
    crossing_events: int
    elapsed_seconds: float
    processing_fps: float
    video_output: Path | None
    events_output: Path | None

    def to_dict(self) -> dict[str, str | int | float | None]:
        return {
            "mode": self.mode.value,
            "source": str(self.source),
            "frames": self.frames,
            "detections": self.detections,
            "tracked_objects": self.tracked_objects,
            "crossing_events": self.crossing_events,
            "elapsed_seconds": round(self.elapsed_seconds, 4),
            "processing_fps": round(self.processing_fps, 2),
            "video_output": None if self.video_output is None else str(self.video_output),
            "events_output": None if self.events_output is None else str(self.events_output),
        }


def _validate_frame(frame: Frame) -> None:
    if (
        not isinstance(frame, np.ndarray)
        or frame.dtype != np.uint8
        or frame.ndim != 3
        or frame.shape[2] != 3
        or frame.size == 0
    ):
        raise ValueError("frame must be a non-empty uint8 BGR image")


def process_frame(
    frame: Frame,
    *,
    frame_index: int,
    mode: PipelineMode,
    config: AppConfig,
    adapter: AnalyticsAdapter,
    state: PipelineState,
    fps: float | None = None,
) -> tuple[FrameResult, PipelineState]:
    """Process one frame without mutating caller-owned state or pixels."""

    _validate_frame(frame)
    if frame_index < 0:
        raise ValueError("frame_index must be non-negative")

    detections: tuple[Detection, ...]
    tracks: tuple[TrackedObject, ...] = ()
    new_events: tuple[CountEvent, ...] = ()
    next_state = state
    if mode is PipelineMode.DETECT:
        detections = adapter.detect(frame)
    else:
        observations = adapter.track(frame)
        detections = tuple(item.detection for item in observations)
        trajectories, tracks = update_trajectories(
            state.trajectories,
            observations,
            frame_index=frame_index,
            frame_size=frame.shape[:2],
            max_length=config.tracking.trajectory_length,
            direction_window=config.tracking.direction_window,
            minimum_displacement=config.tracking.minimum_displacement,
            stale_after=config.tracking.track_buffer,
        )
        counter = state.counter
        if mode is PipelineMode.ANALYZE:
            line = config.counting.line
            counter, new_events = update_counter(
                state.counter,
                tracks,
                frame_index=frame_index,
                frame_size=frame.shape[:2],
                line_start=Point(*line.start),
                line_end=Point(*line.end),
                deadband=config.counting.deadband,
                minimum_track_age=config.counting.minimum_track_age,
                counted_classes=frozenset(config.counting.counted_classes),
                negative_to_positive=CrossingDirection(config.counting.negative_to_positive),
                positive_to_negative=CrossingDirection(config.counting.positive_to_negative),
                stale_after=config.tracking.track_buffer,
            )
        next_state = PipelineState(trajectories=trajectories, counter=counter)

    annotated = render_frame(
        frame,
        detections=detections,
        tracks=tracks,
        all_events=next_state.counter.events,
        config=config,
        fps=fps,
    )
    return (
        FrameResult(frame_index, frame, annotated, detections, tracks, new_events),
        next_state,
    )


def validate_video_source(source: Path) -> Path:
    """Resolve and validate a local video path before loading model weights."""

    resolved = source.resolve(strict=False)
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    if resolved.suffix.lower() not in SUPPORTED_VIDEO_SUFFIXES:
        raise ValueError(f"unsupported video extension: {resolved.suffix or '<none>'}")
    return resolved


def _unique_output_base(output_dir: Path, source: Path, mode: PipelineMode) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{source.stem}-{mode.value}"
    candidate = output_dir / stem
    suffix = 1
    while any(candidate.with_suffix(suffix).exists() for suffix in OUTPUT_ARTIFACT_SUFFIXES):
        candidate = output_dir / f"{stem}.{suffix}"
        suffix += 1
    return candidate


def _write_events(path: Path, events: tuple[CountEvent, ...]) -> None:
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=EVENT_FIELDS)
        writer.writeheader()
        for event in events:
            writer.writerow(
                {
                    "frame_index": event.frame_index,
                    "track_id": event.track_id,
                    "class_name": event.class_name,
                    "direction": event.direction.value,
                }
            )


def _video_fourcc(code: str) -> int:
    if len(code) != 4:
        raise ValueError("video codec must contain four characters")
    builder = cast(
        Callable[[str, str, str, str], int],
        cv2.VideoWriter_fourcc,  # type: ignore[attr-defined]
    )
    return builder(*code)


def _temporary_output_path(output_base: Path, suffix: str) -> Path:
    """Create a same-directory temporary path so the final rename is atomic."""

    return output_base.with_name(f".{output_base.name}.{uuid4().hex}.tmp{suffix}")


def _remove_artifact(path: Path) -> None:
    """Best-effort cleanup for an artifact created by the current run."""

    try:
        path.unlink(missing_ok=True)
    except OSError:
        return


def _publish_artifact(temporary_path: Path, final_path: Path) -> None:
    """Publish a complete same-filesystem artifact without silently overwriting one."""

    if final_path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {final_path}")
    temporary_path.replace(final_path)


def run_video(
    source: Path,
    *,
    mode: PipelineMode,
    config: AppConfig,
    adapter: AnalyticsAdapter,
    preview: bool | None = None,
    max_frames: int | None = None,
) -> RunSummary:
    """Process a local video, safely release resources, and save reproducible outputs."""

    source_path = validate_video_source(source)
    frame_limit = config.video.max_frames if max_frames is None else max_frames
    if frame_limit is not None and frame_limit < 1:
        raise ValueError("max_frames must be positive")
    show_preview = config.video.show_preview if preview is None else preview
    capture = cv2.VideoCapture(str(source_path))
    if not capture.isOpened():
        capture.release()
        raise RuntimeError(f"could not open video: {source_path}")

    state = PipelineState()
    writer: cv2.VideoWriter | None = None
    video_path: Path | None = None
    events_path: Path | None = None
    summary_path: Path | None = None
    temporary_video_path: Path | None = None
    temporary_events_path: Path | None = None
    temporary_summary_path: Path | None = None
    published_paths: list[Path] = []
    total_detections = 0
    total_tracks = 0
    frame_index = 0
    started = perf_counter()
    try:
        source_fps = float(capture.get(cv2.CAP_PROP_FPS))
        source_fps = source_fps if source_fps > 0.0 else 30.0
        output_base = (
            _unique_output_base(config.video.output_dir, source_path, mode)
            if config.video.save_output
            else None
        )
        if output_base is not None:
            video_path = output_base.with_suffix(".mp4")
            events_path = output_base.with_suffix(".events.csv")
            summary_path = output_base.with_suffix(".summary.json")
            temporary_video_path = _temporary_output_path(output_base, ".mp4")
            temporary_events_path = _temporary_output_path(output_base, ".events.csv")
            temporary_summary_path = _temporary_output_path(output_base, ".summary.json")
        while frame_limit is None or frame_index < frame_limit:
            ok, frame = capture.read()
            if not ok:
                break
            validated_frame = cast(Frame, frame)
            elapsed = max(perf_counter() - started, 1e-9)
            result, state = process_frame(
                validated_frame,
                frame_index=frame_index,
                mode=mode,
                config=config,
                adapter=adapter,
                state=state,
                fps=frame_index / elapsed if frame_index else None,
            )
            if output_base is not None:
                if writer is None:
                    height, width = result.annotated_frame.shape[:2]
                    writer = cv2.VideoWriter(
                        str(temporary_video_path),
                        _video_fourcc("mp4v"),
                        source_fps,
                        (width, height),
                    )
                    if not writer.isOpened():
                        raise RuntimeError(f"could not create output video: {video_path}")
                writer.write(result.annotated_frame)
            if show_preview:
                cv2.imshow("Traffic Analytics - press q to stop", result.annotated_frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    frame_index += 1
                    total_detections += len(result.detections)
                    total_tracks += len(result.tracks)
                    break
            total_detections += len(result.detections)
            total_tracks += len(result.tracks)
            frame_index += 1

        if frame_index == 0:
            raise RuntimeError("video contained no decodable frames")
        if writer is not None:
            writer.release()
            writer = None

        elapsed = perf_counter() - started
        summary = RunSummary(
            mode=mode,
            source=source_path,
            frames=frame_index,
            detections=total_detections,
            tracked_objects=total_tracks,
            crossing_events=len(state.counter.events),
            elapsed_seconds=elapsed,
            processing_fps=frame_index / elapsed if elapsed > 0.0 else 0.0,
            video_output=video_path,
            events_output=events_path,
        )
        if config.video.save_output:
            if (
                temporary_video_path is None
                or temporary_events_path is None
                or temporary_summary_path is None
                or video_path is None
                or events_path is None
                or summary_path is None
            ):
                raise RuntimeError("output artifacts were not initialized")
            _write_events(temporary_events_path, state.counter.events)
            temporary_summary_path.write_text(
                json.dumps(summary.to_dict(), indent=2) + "\n",
                encoding="utf-8",
            )
            for temporary_path, final_path in (
                (temporary_video_path, video_path),
                (temporary_events_path, events_path),
                (temporary_summary_path, summary_path),
            ):
                _publish_artifact(temporary_path, final_path)
                published_paths.append(final_path)
        return summary
    except BaseException:
        if writer is not None:
            writer.release()
            writer = None
        for cleanup_path in (
            temporary_video_path,
            temporary_events_path,
            temporary_summary_path,
        ):
            if cleanup_path is not None:
                _remove_artifact(cleanup_path)
        for published_path in published_paths:
            _remove_artifact(published_path)
        raise
    finally:
        capture.release()
        if writer is not None:
            writer.release()
        if show_preview:
            cv2.destroyAllWindows()
