import pytest

from traffic_analytics.counting import CounterState, update_counter
from traffic_analytics.models import (
    BoundingBox,
    CountEvent,
    CrossingDirection,
    Detection,
    MovementDirection,
    Point,
    TrackedObject,
)

LINE_START = Point(0.25, 0.5)
LINE_END = Point(0.75, 0.5)


def _track(
    track_id: int,
    x: float,
    bottom_y: float,
    *,
    class_name: str = "car",
    age: int = 5,
) -> TrackedObject:
    class_id = 0 if class_name == "person" else 2
    detection = Detection(
        class_id,
        class_name,
        0.9,
        BoundingBox(x - 5.0, bottom_y - 10.0, x + 5.0, bottom_y),
    )
    return TrackedObject(
        track_id,
        detection,
        trajectory=(detection.bbox.bottom_center,),
        movement=MovementDirection.DOWN,
        age=age,
    )


def _update(
    state: CounterState,
    track: TrackedObject,
    frame_index: int,
) -> tuple[CounterState, tuple[CountEvent, ...]]:
    return update_counter(
        state,
        (track,),
        frame_index=frame_index,
        frame_size=(100, 100),
        line_start=LINE_START,
        line_end=LINE_END,
        deadband=0.02,
        minimum_track_age=3,
        counted_classes=frozenset({"car", "motorcycle", "bus", "truck", "bicycle"}),
        negative_to_positive=CrossingDirection.IN,
        positive_to_negative=CrossingDirection.OUT,
        stale_after=30,
    )


def test_stable_side_deadband_opposite_side_produces_one_event() -> None:
    state, events = _update(CounterState(), _track(1, 50.0, 30.0), 0)
    assert events == ()
    state, events = _update(state, _track(1, 50.0, 50.5), 1)
    assert events == ()
    state, events = _update(state, _track(1, 50.0, 70.0), 2)

    assert events == (CountEvent(1, "car", CrossingDirection.IN, 2),)
    assert state.events == events


def test_crossing_outside_finite_line_is_not_counted() -> None:
    state, _ = _update(CounterState(), _track(2, 10.0, 30.0), 0)
    state, events = _update(state, _track(2, 10.0, 70.0), 1)

    assert events == ()
    assert state.events == ()


def test_same_track_and_direction_is_counted_only_once() -> None:
    state = CounterState()
    for frame_index, y in enumerate((30.0, 70.0, 30.0, 70.0)):
        state, _ = _update(state, _track(3, 50.0, y), frame_index)

    assert [event.direction for event in state.events] == [
        CrossingDirection.IN,
        CrossingDirection.OUT,
    ]


def test_person_and_young_track_do_not_arm_or_count() -> None:
    state, _ = _update(CounterState(), _track(4, 50.0, 30.0, class_name="person"), 0)
    state, events = _update(state, _track(4, 50.0, 70.0, class_name="person"), 1)
    assert events == ()

    state, _ = _update(CounterState(), _track(5, 50.0, 30.0, age=1), 0)
    state, events = _update(state, _track(5, 50.0, 70.0, age=2), 1)
    assert events == ()


def test_jitter_inside_deadband_never_creates_event() -> None:
    state = CounterState()
    for frame_index, y in enumerate((49.0, 50.5, 49.5, 51.0)):
        state, events = _update(state, _track(6, 50.0, y), frame_index)
        assert events == ()


def test_counter_prunes_stale_track_state_but_preserves_event_history() -> None:
    state, _ = _update(CounterState(), _track(7, 50.0, 30.0), 0)
    state, _ = _update(state, _track(7, 50.0, 70.0), 1)

    new_state, events = update_counter(
        state,
        (),
        frame_index=32,
        frame_size=(100, 100),
        line_start=LINE_START,
        line_end=LINE_END,
        deadband=0.02,
        minimum_track_age=3,
        counted_classes=frozenset({"car"}),
        negative_to_positive=CrossingDirection.IN,
        positive_to_negative=CrossingDirection.OUT,
        stale_after=30,
    )

    assert events == ()
    assert new_state.track_states == ()
    assert len(new_state.events) == 1


def test_expired_track_identity_cannot_emit_a_crossing_event() -> None:
    state, _ = _update(CounterState(), _track(8, 50.0, 30.0), 0)

    new_state, events = update_counter(
        state,
        (_track(8, 50.0, 70.0),),
        frame_index=31,
        frame_size=(100, 100),
        line_start=LINE_START,
        line_end=LINE_END,
        deadband=0.02,
        minimum_track_age=3,
        counted_classes=frozenset({"car"}),
        negative_to_positive=CrossingDirection.IN,
        positive_to_negative=CrossingDirection.OUT,
        stale_after=30,
    )

    assert events == ()
    assert new_state.events == ()


@pytest.mark.parametrize("frame_size", [(0, 100), (100, 0)])
def test_counter_rejects_invalid_frame_size(frame_size: tuple[int, int]) -> None:
    with pytest.raises(ValueError, match="frame"):
        update_counter(
            CounterState(),
            (),
            frame_index=0,
            frame_size=frame_size,
            line_start=LINE_START,
            line_end=LINE_END,
            deadband=0.01,
            minimum_track_age=1,
            counted_classes=frozenset({"car"}),
            negative_to_positive=CrossingDirection.IN,
            positive_to_negative=CrossingDirection.OUT,
            stale_after=30,
        )
