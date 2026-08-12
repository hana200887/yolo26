from dataclasses import FrozenInstanceError
from math import inf

import pytest

from traffic_analytics.models import (
    BoundingBox,
    CountEvent,
    CrossingDirection,
    Detection,
    MovementDirection,
    Point,
    TrackedObject,
)


def test_bounding_box_exposes_center_and_bottom_center() -> None:
    bbox = BoundingBox(10.0, 20.0, 30.0, 60.0)

    assert bbox.center == Point(20.0, 40.0)
    assert bbox.bottom_center == Point(20.0, 60.0)


@pytest.mark.parametrize(
    "coordinates",
    [
        (10.0, 10.0, 10.0, 20.0),
        (10.0, 10.0, 20.0, 10.0),
        (20.0, 10.0, 10.0, 20.0),
        (10.0, 20.0, 20.0, 10.0),
        (0.0, 0.0, inf, 10.0),
    ],
)
def test_bounding_box_rejects_invalid_coordinates(
    coordinates: tuple[float, float, float, float],
) -> None:
    with pytest.raises(ValueError):
        BoundingBox(*coordinates)


def test_detection_is_immutable_and_validated() -> None:
    detection = Detection(
        class_id=2,
        class_name="car",
        confidence=0.91,
        bbox=BoundingBox(1.0, 2.0, 11.0, 22.0),
    )

    with pytest.raises(FrozenInstanceError):
        detection.confidence = 0.5  # type: ignore[misc]

    with pytest.raises(ValueError, match="confidence"):
        Detection(2, "car", 1.01, detection.bbox)

    with pytest.raises(ValueError, match="class_name"):
        Detection(2, " ", 0.5, detection.bbox)


def test_tracked_object_keeps_immutable_trajectory() -> None:
    tracked = TrackedObject(
        track_id=7,
        detection=Detection(2, "car", 0.88, BoundingBox(0.0, 0.0, 20.0, 10.0)),
        trajectory=(Point(5.0, 5.0), Point(10.0, 5.0)),
        movement=MovementDirection.RIGHT,
        age=4,
    )

    assert tracked.center == Point(10.0, 5.0)
    assert isinstance(tracked.trajectory, tuple)

    with pytest.raises(FrozenInstanceError):
        tracked.track_id = 8  # type: ignore[misc]

    with pytest.raises(ValueError, match="track_id"):
        TrackedObject(0, tracked.detection)


def test_count_event_rejects_non_vehicle_metadata() -> None:
    event = CountEvent(
        track_id=3,
        class_name="motorcycle",
        direction=CrossingDirection.IN,
        frame_index=42,
    )

    assert event.direction is CrossingDirection.IN

    with pytest.raises(ValueError, match="frame_index"):
        CountEvent(3, "motorcycle", CrossingDirection.OUT, -1)
