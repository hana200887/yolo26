"""Immutable domain objects shared by the traffic analytics pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite


@dataclass(frozen=True, slots=True)
class Point:
    """A point in image or normalized coordinates."""

    x: float
    y: float

    def __post_init__(self) -> None:
        if not isfinite(self.x) or not isfinite(self.y):
            raise ValueError("point coordinates must be finite")


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """An axis-aligned bounding box in ``xyxy`` pixel coordinates."""

    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        coordinates = (self.x1, self.y1, self.x2, self.y2)
        if not all(isfinite(value) for value in coordinates):
            raise ValueError("bounding-box coordinates must be finite")
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("bounding box must have positive width and height")

    @property
    def center(self) -> Point:
        """Return the geometric center of the box."""

        return Point((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    @property
    def bottom_center(self) -> Point:
        """Return the road-contact proxy used for line crossing."""

        return Point((self.x1 + self.x2) / 2.0, self.y2)


@dataclass(frozen=True, slots=True)
class Detection:
    """A detector output independent of Ultralytics result types."""

    class_id: int
    class_name: str
    confidence: float
    bbox: BoundingBox

    def __post_init__(self) -> None:
        if self.class_id < 0:
            raise ValueError("class_id must be non-negative")
        if not self.class_name.strip():
            raise ValueError("class_name must not be blank")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


class MovementDirection(StrEnum):
    """Coarse motion direction in image coordinates."""

    UNKNOWN = "UNKNOWN"
    STATIONARY = "STATIONARY"
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class CrossingDirection(StrEnum):
    """Configured semantic direction of a line-crossing event."""

    IN = "IN"
    OUT = "OUT"


@dataclass(frozen=True, slots=True)
class TrackObservation:
    """A tracker output before project-owned trajectory enrichment."""

    track_id: int
    detection: Detection
    age: int = 1

    def __post_init__(self) -> None:
        if self.track_id <= 0:
            raise ValueError("track_id must be positive")
        if self.age <= 0:
            raise ValueError("age must be positive")

    @property
    def anchor(self) -> Point:
        """Return the bottom-center road-contact proxy."""

        return self.detection.bbox.bottom_center


@dataclass(frozen=True, slots=True)
class TrackHistory:
    """Bounded point history for one tracker identity."""

    track_id: int
    points: tuple[Point, ...]
    last_seen_frame: int

    def __post_init__(self) -> None:
        if self.track_id <= 0:
            raise ValueError("track_id must be positive")
        if not isinstance(self.points, tuple):
            raise TypeError("points must be an immutable tuple")
        if self.last_seen_frame < 0:
            raise ValueError("last_seen_frame must be non-negative")


@dataclass(frozen=True, slots=True)
class TrajectoryState:
    """Immutable collection of active and recently lost track histories."""

    histories: tuple[TrackHistory, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.histories, tuple):
            raise TypeError("histories must be an immutable tuple")
        track_ids = tuple(history.track_id for history in self.histories)
        if len(track_ids) != len(set(track_ids)):
            raise ValueError("trajectory state contains duplicate track IDs")


@dataclass(frozen=True, slots=True)
class TrackedObject:
    """A tracked detection enriched with project-owned temporal state."""

    track_id: int
    detection: Detection
    trajectory: tuple[Point, ...] = ()
    movement: MovementDirection = MovementDirection.UNKNOWN
    age: int = 1

    def __post_init__(self) -> None:
        if self.track_id <= 0:
            raise ValueError("track_id must be positive")
        if self.age <= 0:
            raise ValueError("age must be positive")
        if not isinstance(self.trajectory, tuple):
            raise TypeError("trajectory must be an immutable tuple")

    @property
    def center(self) -> Point:
        """Return the current box center."""

        return self.detection.bbox.center

    @property
    def anchor(self) -> Point:
        """Return the bottom-center road-contact proxy."""

        return self.detection.bbox.bottom_center


@dataclass(frozen=True, slots=True)
class CountEvent:
    """A single deduplicated line-crossing event."""

    track_id: int
    class_name: str
    direction: CrossingDirection
    frame_index: int

    def __post_init__(self) -> None:
        if self.track_id <= 0:
            raise ValueError("track_id must be positive")
        if not self.class_name.strip():
            raise ValueError("class_name must not be blank")
        if self.frame_index < 0:
            raise ValueError("frame_index must be non-negative")
