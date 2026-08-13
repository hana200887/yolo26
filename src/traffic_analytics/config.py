"""Validated YAML configuration for the traffic analytics pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from traffic_analytics.geometry import MINIMUM_LINE_LENGTH

MAX_CONFIG_BYTES = 1_000_000
VEHICLE_CLASSES = frozenset({"bicycle", "bus", "car", "motorcycle", "truck"})
SUPPORTED_CLASSES = VEHICLE_CLASSES | {"person"}
NormalizedCoordinate = Annotated[float, Field(ge=0.0, le=1.0)]
Probability = Annotated[float, Field(ge=0.0, le=1.0)]


class FrozenConfig(BaseModel):
    """Base configuration that rejects typos and runtime mutation."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelConfig(FrozenConfig):
    """YOLO inference configuration."""

    weights: Literal["yolo26n.pt"]
    device: str = "auto"
    inference_confidence: Probability
    display_confidence: Probability
    end2end: bool = True
    image_size: Annotated[int, Field(ge=320, le=2048)] = 640
    tracked_classes: tuple[str, ...]

    @field_validator("device")
    @classmethod
    def validate_device(cls, value: str) -> str:
        if value in {"auto", "cpu", "cuda"}:
            return value
        if value.startswith("cuda:") and value.removeprefix("cuda:").isdigit():
            return value
        raise ValueError("device must be auto, cpu, cuda, or cuda:<index>")

    @field_validator("tracked_classes")
    @classmethod
    def validate_tracked_classes(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if not values or len(values) != len(set(values)):
            raise ValueError("tracked_classes must be non-empty and unique")
        unknown = set(values) - SUPPORTED_CLASSES
        if unknown:
            raise ValueError(f"unsupported tracked_classes: {sorted(unknown)}")
        return values

    @model_validator(mode="after")
    def validate_display_threshold(self) -> ModelConfig:
        if self.display_confidence < self.inference_confidence:
            raise ValueError("display_confidence must not be below inference_confidence")
        return self


class TrackingConfig(FrozenConfig):
    """ByteTrack and trajectory settings."""

    tracker_config: Path
    tracker_type: Literal["bytetrack"]
    track_high_thresh: Probability
    track_low_thresh: Probability
    new_track_thresh: Probability
    track_buffer: Annotated[int, Field(ge=1, le=10_000)]
    match_thresh: Probability
    fuse_score: bool
    trajectory_length: Annotated[int, Field(ge=2, le=10_000)]
    direction_window: Annotated[int, Field(ge=2, le=10_000)]
    minimum_displacement: Annotated[float, Field(gt=0.0, le=1.0)]

    @model_validator(mode="after")
    def validate_thresholds_and_history(self) -> TrackingConfig:
        if self.track_low_thresh > self.track_high_thresh:
            raise ValueError("track_low_thresh must not exceed track_high_thresh")
        if self.new_track_thresh < self.track_high_thresh:
            raise ValueError("new_track_thresh must not be below track_high_thresh")
        if self.direction_window > self.trajectory_length:
            raise ValueError("direction_window must not exceed trajectory_length")
        return self


class CountingLineConfig(FrozenConfig):
    """A directed line segment in normalized frame coordinates."""

    start: tuple[NormalizedCoordinate, NormalizedCoordinate]
    end: tuple[NormalizedCoordinate, NormalizedCoordinate]

    @model_validator(mode="after")
    def validate_line(self) -> CountingLineConfig:
        horizontal = self.end[0] - self.start[0]
        vertical = self.end[1] - self.start[1]
        if horizontal**2 + vertical**2 <= MINIMUM_LINE_LENGTH**2:
            raise ValueError("counting line endpoints must be different")
        return self


class CountingConfig(FrozenConfig):
    """Line-crossing and class aggregation settings."""

    counted_classes: tuple[str, ...]
    line: CountingLineConfig
    deadband: Annotated[float, Field(ge=0.0, le=0.25)]
    minimum_track_age: Annotated[int, Field(ge=1, le=10_000)]
    negative_to_positive: Literal["IN", "OUT"]
    positive_to_negative: Literal["IN", "OUT"]

    @field_validator("counted_classes")
    @classmethod
    def validate_counted_classes(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if not values or len(values) != len(set(values)):
            raise ValueError("counted_classes must be non-empty and unique")
        unknown = set(values) - VEHICLE_CLASSES
        if unknown:
            raise ValueError(
                f"counted_classes must contain only vehicle classes: {sorted(unknown)}"
            )
        return values

    @model_validator(mode="after")
    def validate_direction_labels(self) -> CountingConfig:
        if self.negative_to_positive == self.positive_to_negative:
            raise ValueError("crossing direction labels must be different")
        return self


class VideoConfig(FrozenConfig):
    """Video source and output defaults."""

    show_preview: bool
    save_output: bool
    output_dir: Path
    max_frames: Annotated[int, Field(ge=1)] | None


class VisualizationConfig(FrozenConfig):
    """Overlay feature switches."""

    show_detections: bool
    show_track_ids: bool
    show_trajectories: bool
    show_counting_line: bool
    show_statistics: bool
    show_fps: bool


class AppConfig(FrozenConfig):
    """Complete application configuration."""

    model: ModelConfig
    tracking: TrackingConfig
    counting: CountingConfig
    video: VideoConfig
    visualization: VisualizationConfig

    @model_validator(mode="after")
    def validate_cross_section_contracts(self) -> AppConfig:
        if self.model.inference_confidence > self.tracking.track_low_thresh:
            raise ValueError("inference_confidence must not exceed track_low_thresh")
        if not set(self.counting.counted_classes).issubset(self.model.tracked_classes):
            raise ValueError("counted_classes must be a subset of tracked_classes")
        return self


def _read_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.stat().st_size > MAX_CONFIG_BYTES:
        raise ValueError("configuration file must not exceed 1 MB")
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"could not read YAML configuration: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("configuration root must be a mapping")
    return payload


def load_config(path: Path) -> AppConfig:
    """Load an application config and its colocated ByteTrack config."""

    config_path = path.resolve(strict=False)
    payload = _read_yaml_mapping(config_path)
    tracking = payload.get("tracking")
    if not isinstance(tracking, dict):
        raise ValueError("tracking configuration must be a mapping")

    tracker_name = tracking.get("tracker_config")
    if not isinstance(tracker_name, str) or Path(tracker_name).name != tracker_name:
        raise ValueError("tracker_config must name a YAML file beside the application config")
    if Path(tracker_name).suffix.lower() not in {".yaml", ".yml"}:
        raise ValueError("tracker_config must use a YAML extension")

    tracker_path = config_path.parent / tracker_name
    tracker_payload = _read_yaml_mapping(tracker_path)
    merged_tracking = {**tracking, **tracker_payload, "tracker_config": tracker_path}
    video = payload.get("video")
    if not isinstance(video, dict):
        raise ValueError("video configuration must be a mapping")
    output_value = video.get("output_dir")
    if not isinstance(output_value, str) or not output_value.strip():
        raise ValueError("video.output_dir must be a non-empty path")
    output_dir = Path(output_value)
    if not output_dir.is_absolute():
        output_dir = (config_path.parent / output_dir).resolve(strict=False)
    merged_video = {**video, "output_dir": output_dir}
    merged_payload = {**payload, "tracking": merged_tracking, "video": merged_video}
    return AppConfig.model_validate(merged_payload)
