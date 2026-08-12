from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
import pytest

from traffic_analytics.config import load_config
from traffic_analytics.models import Detection, TrackObservation
from traffic_analytics.ultralytics_adapter import AdapterError, UltralyticsAdapter

ROOT = Path(__file__).parents[2]


@dataclass
class FakeBoxes:
    xyxy: np.ndarray[Any, np.dtype[np.float32]]
    conf: np.ndarray[Any, np.dtype[np.float32]]
    cls: np.ndarray[Any, np.dtype[np.float32]]
    id: np.ndarray[Any, np.dtype[np.float32]] | None = None


@dataclass
class FakeResult:
    boxes: FakeBoxes | None


class FakeModel:
    names: ClassVar[dict[int, str]] = {
        0: "person",
        1: "bicycle",
        2: "car",
        3: "motorcycle",
        4: "airplane",
        5: "bus",
        7: "truck",
    }

    def __init__(
        self,
        predict_results: list[list[FakeResult]] | None = None,
        track_results: list[list[FakeResult]] | None = None,
    ) -> None:
        self.predict_results = list(predict_results or [])
        self.track_results = list(track_results or [])
        self.predict_calls: list[dict[str, object]] = []
        self.track_calls: list[dict[str, object]] = []

    def predict(self, **kwargs: object) -> list[FakeResult]:
        self.predict_calls.append(kwargs)
        return self.predict_results.pop(0) if self.predict_results else []

    def track(self, **kwargs: object) -> list[FakeResult]:
        self.track_calls.append(kwargs)
        return self.track_results.pop(0) if self.track_results else []


def _boxes(
    rows: list[tuple[float, float, float, float, float, float]],
    track_ids: list[float] | None = None,
) -> FakeBoxes:
    array = np.asarray(rows, dtype=np.float32)
    if not rows:
        array = np.empty((0, 6), dtype=np.float32)
    ids = None if track_ids is None else np.asarray(track_ids, dtype=np.float32)
    return FakeBoxes(array[:, :4], array[:, 4], array[:, 5], ids)


def _adapter(model: FakeModel) -> UltralyticsAdapter:
    config = load_config(ROOT / "configs" / "default.yaml")
    return UltralyticsAdapter(config.model, config.tracking, model_factory=lambda _: model)


def test_detect_maps_allowed_classes_and_keeps_low_confidence_boxes() -> None:
    model = FakeModel(
        predict_results=[
            [
                FakeResult(
                    _boxes(
                        [
                            (10.0, 20.0, 30.0, 40.0, 0.15, 2.0),
                            (1.0, 2.0, 11.0, 12.0, 0.95, 4.0),
                        ]
                    )
                )
            ]
        ]
    )
    adapter = _adapter(model)

    detections = adapter.detect(np.zeros((64, 96, 3), dtype=np.uint8))

    assert len(detections) == 1
    assert detections[0].class_id == 2
    assert detections[0].class_name == "car"
    assert detections[0].confidence == pytest.approx(0.15)
    assert detections[0].bbox == Detection(2, "car", 0.15, detections[0].bbox).bbox
    assert model.predict_calls[0]["conf"] == pytest.approx(0.10)
    assert model.predict_calls[0]["classes"] == [0, 1, 2, 3, 5, 7]
    assert model.predict_calls[0]["device"] is None
    assert model.predict_calls[0]["end2end"] is True
    assert model.predict_calls[0]["imgsz"] == 640


def test_track_uses_public_persistent_api_and_returns_domain_objects() -> None:
    frame_result = [FakeResult(_boxes([(10, 20, 30, 40, 0.2, 2)], [12]))]
    model = FakeModel(track_results=[frame_result, frame_result])
    adapter = _adapter(model)
    frame = np.zeros((64, 96, 3), dtype=np.uint8)

    first = adapter.track(frame)
    second = adapter.track(frame)

    assert isinstance(first[0], TrackObservation)
    assert first[0].track_id == 12
    assert first[0].detection.class_name == "car"
    assert first[0].detection.confidence == pytest.approx(0.2)
    assert first[0].age == 1
    assert second[0].age == 2
    assert model.track_calls[0]["persist"] is True
    assert model.track_calls[0]["conf"] == pytest.approx(0.10)
    assert model.track_calls[0]["tracker"] == str(ROOT / "configs" / "bytetrack.yaml")


def test_track_without_confirmed_ids_returns_empty_tuple() -> None:
    model = FakeModel(track_results=[[FakeResult(_boxes([(1, 1, 5, 5, 0.8, 2)]))]])

    assert _adapter(model).track(np.zeros((10, 10, 3), dtype=np.uint8)) == ()


def test_track_keeps_age_through_short_empty_tracker_gap() -> None:
    tracked = FakeResult(_boxes([(10, 20, 30, 40, 0.9, 2)], [12]))
    no_confirmed_ids = FakeResult(_boxes([(10, 20, 30, 40, 0.2, 2)]))
    adapter = _adapter(FakeModel(track_results=[[tracked], [no_confirmed_ids], [tracked]]))
    frame = np.zeros((64, 96, 3), dtype=np.uint8)

    assert adapter.track(frame)[0].age == 1
    assert adapter.track(frame) == ()
    assert adapter.track(frame)[0].age == 3


def test_track_prunes_age_after_tracker_buffer_expires() -> None:
    tracked = FakeResult(_boxes([(10, 20, 30, 40, 0.9, 2)], [12]))
    no_confirmed_ids = FakeResult(_boxes([(10, 20, 30, 40, 0.2, 2)]))
    config = load_config(ROOT / "configs" / "default.yaml")
    tracking = config.tracking.model_copy(update={"track_buffer": 1})
    adapter = UltralyticsAdapter(
        config.model,
        tracking,
        model_factory=lambda _: FakeModel(
            track_results=[[tracked], [no_confirmed_ids], [no_confirmed_ids], [tracked]]
        ),
    )
    frame = np.zeros((64, 96, 3), dtype=np.uint8)

    assert adapter.track(frame)[0].age == 1
    assert adapter.track(frame) == ()
    assert adapter.track(frame) == ()
    assert adapter.track(frame)[0].age == 1


@pytest.mark.parametrize(
    "frame",
    [
        np.empty((0, 10, 3), dtype=np.uint8),
        np.zeros((10, 10), dtype=np.uint8),
        np.zeros((10, 10, 4), dtype=np.uint8),
        np.zeros((10, 10, 3), dtype=np.float32),
    ],
)
def test_adapter_rejects_invalid_opencv_frames(frame: np.ndarray[Any, Any]) -> None:
    adapter = _adapter(FakeModel())

    with pytest.raises(ValueError, match="frame"):
        adapter.detect(frame)


def test_adapter_rejects_malformed_backend_output() -> None:
    malformed = FakeBoxes(
        xyxy=np.asarray([[0, 0, 10, 10]], dtype=np.float32),
        conf=np.asarray([], dtype=np.float32),
        cls=np.asarray([2], dtype=np.float32),
    )
    adapter = _adapter(FakeModel(predict_results=[[FakeResult(malformed)]]))

    with pytest.raises(AdapterError, match="inconsistent"):
        adapter.detect(np.zeros((10, 10, 3), dtype=np.uint8))


def test_model_factory_receives_only_the_trusted_official_alias() -> None:
    received: list[str] = []

    def factory(weights: str) -> FakeModel:
        received.append(weights)
        return FakeModel()

    config = load_config(ROOT / "configs" / "default.yaml")
    adapter = UltralyticsAdapter(config.model, config.tracking, model_factory=factory)

    assert received == ["yolo26n.pt"]
    assert adapter.detect(np.zeros((10, 10, 3), dtype=np.uint8)) == ()
