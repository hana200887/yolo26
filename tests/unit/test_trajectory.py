from dataclasses import FrozenInstanceError

import pytest

from traffic_analytics.models import (
    BoundingBox,
    Detection,
    MovementDirection,
    TrackObservation,
    TrajectoryState,
)
from traffic_analytics.trajectory import update_trajectories


def _observation(track_id: int, x: float, y: float, *, age: int) -> TrackObservation:
    return TrackObservation(
        track_id=track_id,
        detection=Detection(2, "car", 0.9, BoundingBox(x - 5.0, y - 10.0, x + 5.0, y)),
        age=age,
    )


def _advance(
    state: TrajectoryState,
    observation: TrackObservation,
    frame_index: int,
    *,
    frame_size: tuple[int, int] = (100, 100),
    max_length: int = 5,
    direction_window: int = 3,
    minimum_displacement: float = 0.01,
) -> tuple[TrajectoryState, MovementDirection]:
    new_state, tracked = update_trajectories(
        state,
        (observation,),
        frame_index=frame_index,
        frame_size=frame_size,
        max_length=max_length,
        direction_window=direction_window,
        minimum_displacement=minimum_displacement,
        stale_after=30,
    )
    assert len(tracked) == 1
    return new_state, tracked[0].movement


def test_trajectory_state_is_immutable_and_history_is_bounded() -> None:
    original = TrajectoryState()
    state = original
    for frame_index in range(7):
        state, _ = _advance(
            state,
            _observation(1, 10.0 + frame_index, 20.0, age=frame_index + 1),
            frame_index,
        )

    assert original.histories == ()
    assert len(state.histories[0].points) == 5
    assert state.histories[0].points[0].x == pytest.approx(12.0)

    with pytest.raises(FrozenInstanceError):
        state.histories = ()  # type: ignore[misc]


@pytest.mark.parametrize(
    ("positions", "expected"),
    [
        (((50.0, 50.0), (40.0, 50.0), (30.0, 50.0)), MovementDirection.LEFT),
        (((30.0, 50.0), (40.0, 50.0), (50.0, 50.0)), MovementDirection.RIGHT),
        (((50.0, 50.0), (50.0, 40.0), (50.0, 30.0)), MovementDirection.UP),
        (((50.0, 30.0), (50.0, 40.0), (50.0, 50.0)), MovementDirection.DOWN),
        (((50.0, 50.0), (50.2, 50.1), (50.3, 50.2)), MovementDirection.STATIONARY),
    ],
)
def test_direction_uses_a_window_and_normalized_displacement(
    positions: tuple[tuple[float, float], ...],
    expected: MovementDirection,
) -> None:
    state = TrajectoryState()
    movement = MovementDirection.UNKNOWN
    for frame_index, (x, y) in enumerate(positions):
        state, movement = _advance(
            state,
            _observation(1, x, y, age=frame_index + 1),
            frame_index,
        )

    assert movement is expected


def test_direction_is_unknown_until_window_is_full() -> None:
    state, movement = _advance(
        TrajectoryState(),
        _observation(2, 10.0, 10.0, age=1),
        0,
    )

    assert movement is MovementDirection.UNKNOWN
    assert state.histories[0].last_seen_frame == 0


def test_normalized_direction_is_resolution_invariant() -> None:
    state_small = TrajectoryState()
    state_large = TrajectoryState()
    movement_small = MovementDirection.UNKNOWN
    movement_large = MovementDirection.UNKNOWN
    for frame_index, fraction in enumerate((0.2, 0.3, 0.4)):
        state_small, movement_small = _advance(
            state_small,
            _observation(1, fraction * 100, 50.0, age=frame_index + 1),
            frame_index,
            frame_size=(100, 100),
        )
        state_large, movement_large = _advance(
            state_large,
            _observation(1, fraction * 1000, 500.0, age=frame_index + 1),
            frame_index,
            frame_size=(1000, 1000),
        )

    assert movement_small is MovementDirection.RIGHT
    assert movement_large is movement_small


def test_stale_history_is_pruned_without_mutating_previous_state() -> None:
    state, _ = _advance(TrajectoryState(), _observation(1, 10.0, 10.0, age=1), 0)

    new_state, tracked = update_trajectories(
        state,
        (),
        frame_index=31,
        frame_size=(100, 100),
        max_length=5,
        direction_window=3,
        minimum_displacement=0.01,
        stale_after=30,
    )

    assert state.histories
    assert new_state.histories == ()
    assert tracked == ()
