"""Immutable trajectory state transitions and coarse motion estimation."""

from __future__ import annotations

from collections.abc import Sequence
from math import hypot

from traffic_analytics.models import (
    MovementDirection,
    TrackedObject,
    TrackHistory,
    TrackObservation,
    TrajectoryState,
)


def _movement_direction(
    history: TrackHistory,
    *,
    frame_size: tuple[int, int],
    direction_window: int,
    minimum_displacement: float,
) -> MovementDirection:
    if len(history.points) < direction_window:
        return MovementDirection.UNKNOWN

    height, width = frame_size
    start = history.points[-direction_window]
    end = history.points[-1]
    delta_x = (end.x - start.x) / width
    delta_y = (end.y - start.y) / height
    if hypot(delta_x, delta_y) < minimum_displacement:
        return MovementDirection.STATIONARY
    if abs(delta_x) >= abs(delta_y):
        return MovementDirection.RIGHT if delta_x > 0.0 else MovementDirection.LEFT
    return MovementDirection.DOWN if delta_y > 0.0 else MovementDirection.UP


def update_trajectories(
    state: TrajectoryState,
    observations: Sequence[TrackObservation],
    *,
    frame_index: int,
    frame_size: tuple[int, int],
    max_length: int,
    direction_window: int,
    minimum_displacement: float,
    stale_after: int,
) -> tuple[TrajectoryState, tuple[TrackedObject, ...]]:
    """Advance trajectory histories without mutating the previous state."""

    height, width = frame_size
    if height <= 0 or width <= 0:
        raise ValueError("frame dimensions must be positive")
    if frame_index < 0:
        raise ValueError("frame_index must be non-negative")
    if max_length < 2 or not 2 <= direction_window <= max_length:
        raise ValueError("direction_window must be between 2 and max_length")
    if not 0.0 < minimum_displacement <= 1.0:
        raise ValueError("minimum_displacement must be between 0 and 1")
    if stale_after < 0:
        raise ValueError("stale_after must be non-negative")

    previous = {history.track_id: history for history in state.histories}
    observation_ids = tuple(observation.track_id for observation in observations)
    if len(observation_ids) != len(set(observation_ids)):
        raise ValueError("observations contain duplicate track IDs")

    next_histories: dict[int, TrackHistory] = {
        track_id: history
        for track_id, history in previous.items()
        if frame_index - history.last_seen_frame <= stale_after
    }
    tracked_objects: list[TrackedObject] = []

    for observation in observations:
        previous_points = previous.get(observation.track_id)
        old_points = previous_points.points if previous_points is not None else ()
        points = (*old_points, observation.anchor)[-max_length:]
        history = TrackHistory(observation.track_id, points, frame_index)
        next_histories[observation.track_id] = history
        tracked_objects.append(
            TrackedObject(
                track_id=observation.track_id,
                detection=observation.detection,
                trajectory=history.points,
                movement=_movement_direction(
                    history,
                    frame_size=frame_size,
                    direction_window=direction_window,
                    minimum_displacement=minimum_displacement,
                ),
                age=observation.age,
            )
        )

    next_state = TrajectoryState(
        tuple(sorted(next_histories.values(), key=lambda item: item.track_id))
    )
    return next_state, tuple(tracked_objects)
