"""Narrow, validated boundary around the public Ultralytics APIs."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from math import isfinite
from typing import Any, Protocol, cast

import numpy as np
from numpy.typing import NDArray

from traffic_analytics.config import ModelConfig, TrackingConfig
from traffic_analytics.models import BoundingBox, Detection, TrackObservation

Frame = NDArray[np.uint8]


class AdapterError(RuntimeError):
    """Raised when an inference backend violates the adapter contract."""


class ModelLike(Protocol):
    """Small portion of the Ultralytics model API used by this project."""

    names: Mapping[int, str] | Sequence[str]

    def predict(self, **kwargs: object) -> Sequence[object]: ...

    def track(self, **kwargs: object) -> Sequence[object]: ...


ModelFactory = Callable[[str], ModelLike]


def _default_model_factory(weights: str) -> ModelLike:
    from ultralytics import YOLO  # type: ignore[attr-defined]

    return cast(ModelLike, YOLO(weights))


def _as_array(value: object, field_name: str) -> NDArray[np.generic]:
    """Convert a tensor-like backend value without leaking tensor types."""

    current: Any = value
    if hasattr(current, "detach"):
        current = current.detach()
    if hasattr(current, "cpu"):
        current = current.cpu()
    if hasattr(current, "numpy"):
        current = current.numpy()
    try:
        return np.asarray(current)
    except (TypeError, ValueError) as exc:
        raise AdapterError(f"could not convert backend field {field_name}") from exc


class UltralyticsAdapter:
    """Translate public ``predict``/``track`` results into immutable domain objects."""

    def __init__(
        self,
        model_config: ModelConfig,
        tracking_config: TrackingConfig,
        model_factory: ModelFactory | None = None,
    ) -> None:
        self._model_config = model_config
        self._tracking_config = tracking_config
        self._model = (model_factory or _default_model_factory)(model_config.weights)
        self._class_names = self._normalized_names(self._model.names)
        allowed = set(model_config.tracked_classes)
        self._class_ids = sorted(
            class_id for class_id, name in self._class_names.items() if name in allowed
        )
        missing = allowed - set(self._class_names.values())
        if missing:
            raise AdapterError(f"model does not define configured classes: {sorted(missing)}")
        self._tracking_frame_index = 0
        self._track_ages: tuple[tuple[int, int, int], ...] = ()

    @staticmethod
    def _normalized_names(names: Mapping[int, str] | Sequence[str]) -> dict[int, str]:
        items = names.items() if isinstance(names, Mapping) else enumerate(names)
        normalized = {int(class_id): str(name) for class_id, name in items}
        if not normalized or any(
            class_id < 0 or not name.strip() for class_id, name in normalized.items()
        ):
            raise AdapterError("model class names are malformed")
        return normalized

    @staticmethod
    def _validate_frame(frame: Frame) -> None:
        if (
            not isinstance(frame, np.ndarray)
            or frame.dtype != np.uint8
            or frame.ndim != 3
            or frame.shape[2] != 3
            or frame.size == 0
        ):
            raise ValueError("frame must be a non-empty uint8 BGR image")

    def _common_arguments(self, frame: Frame) -> dict[str, object]:
        device = None if self._model_config.device == "auto" else self._model_config.device
        return {
            "source": frame,
            "conf": self._model_config.inference_confidence,
            "classes": self._class_ids,
            "device": device,
            "imgsz": self._model_config.image_size,
            "end2end": self._model_config.end2end,
            "verbose": False,
        }

    def detect(self, frame: Frame) -> tuple[Detection, ...]:
        """Run one-frame detection with the low ByteTrack admission threshold."""

        self._validate_frame(frame)
        results = self._model.predict(**self._common_arguments(frame))
        return self._parse_detections(results)

    def track(self, frame: Frame) -> tuple[TrackObservation, ...]:
        """Run the public persistent ByteTrack API and return confirmed identities."""

        self._validate_frame(frame)
        self._tracking_frame_index += 1
        results = self._model.track(
            **self._common_arguments(frame),
            persist=True,
            tracker=str(self._tracking_config.tracker_config),
        )
        detections, track_ids = self._parse_result_arrays(results)
        previous_ages = {
            track_id: (age, last_seen_frame)
            for track_id, age, last_seen_frame in self._track_ages
            if self._tracking_frame_index - last_seen_frame <= self._tracking_config.track_buffer
        }
        if track_ids is None:
            self._track_ages = tuple(
                sorted(
                    (track_id, age, last_seen_frame)
                    for track_id, (age, last_seen_frame) in previous_ages.items()
                )
            )
            return ()

        current_ages: dict[int, int] = {}
        for track_id in track_ids:
            prior = previous_ages.get(track_id)
            current_ages[track_id] = (
                1 if prior is None else prior[0] + self._tracking_frame_index - prior[1]
            )
            previous_ages[track_id] = (current_ages[track_id], self._tracking_frame_index)
        self._track_ages = tuple(
            sorted(
                (track_id, age, last_seen_frame)
                for track_id, (age, last_seen_frame) in previous_ages.items()
            )
        )
        return tuple(
            TrackObservation(track_id, detection, current_ages[track_id])
            for track_id, detection in zip(track_ids, detections, strict=True)
        )

    def _parse_detections(self, results: Sequence[object]) -> tuple[Detection, ...]:
        detections, _ = self._parse_result_arrays(results)
        return detections

    def _parse_result_arrays(
        self, results: Sequence[object]
    ) -> tuple[tuple[Detection, ...], tuple[int, ...] | None]:
        if not results:
            return (), None
        boxes = getattr(results[0], "boxes", None)
        if boxes is None:
            return (), None

        xyxy = _as_array(getattr(boxes, "xyxy", None), "xyxy")
        confidence = _as_array(getattr(boxes, "conf", None), "conf").reshape(-1)
        class_ids = _as_array(getattr(boxes, "cls", None), "cls").reshape(-1)
        if xyxy.ndim != 2 or xyxy.shape[1:] != (4,):
            raise AdapterError("backend xyxy output must have shape (N, 4)")
        row_count = xyxy.shape[0]
        if confidence.size != row_count or class_ids.size != row_count:
            raise AdapterError("backend output arrays have inconsistent lengths")

        raw_ids = getattr(boxes, "id", None)
        ids_array = None if raw_ids is None else _as_array(raw_ids, "id").reshape(-1)
        if ids_array is not None and ids_array.size != row_count:
            raise AdapterError("backend track IDs have inconsistent lengths")

        detections: list[Detection] = []
        track_ids: list[int] | None = [] if ids_array is not None else None
        for index in range(row_count):
            class_value = float(class_ids[index])
            if not isfinite(class_value) or not class_value.is_integer():
                raise AdapterError("backend class IDs must be finite integers")
            class_id = int(class_value)
            class_name = self._class_names.get(class_id)
            if class_name not in self._model_config.tracked_classes:
                continue
            try:
                detection = Detection(
                    class_id=class_id,
                    class_name=class_name,
                    confidence=float(confidence[index]),
                    bbox=BoundingBox(*(float(value) for value in xyxy[index])),
                )
            except (TypeError, ValueError) as exc:
                raise AdapterError(f"invalid backend detection at row {index}") from exc
            detections.append(detection)
            if track_ids is not None and ids_array is not None:
                track_value = float(ids_array[index])
                if not isfinite(track_value) or not track_value.is_integer() or track_value <= 0:
                    raise AdapterError("backend track IDs must be positive integers")
                track_ids.append(int(track_value))

        return tuple(detections), None if track_ids is None else tuple(track_ids)
