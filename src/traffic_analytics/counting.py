"""Immutable, finite-segment vehicle line-crossing state machine."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from traffic_analytics.geometry import line_side, normalize_point, segments_intersect
from traffic_analytics.models import CountEvent, CrossingDirection, Point, TrackedObject

EventStatistic = tuple[CrossingDirection, str, int]


@dataclass(frozen=True, slots=True)
class TrackCrossingState:
    """Last stable side and point observed for one track."""

    track_id: int
    stable_side: int
    stable_point: Point
    last_seen_frame: int

    def __post_init__(self) -> None:
        if self.track_id <= 0:
            raise ValueError("track_id must be positive")
        if self.stable_side not in {-1, 1}:
            raise ValueError("stable_side must be -1 or 1")
        if self.last_seen_frame < 0:
            raise ValueError("last_seen_frame must be non-negative")


@dataclass(frozen=True, slots=True)
class CounterState:
    """Line-crossing state, dedupe keys, and accumulated events."""

    track_states: tuple[TrackCrossingState, ...] = ()
    counted: frozenset[tuple[int, CrossingDirection]] = frozenset()
    events: tuple[CountEvent, ...] = ()
    statistics: tuple[EventStatistic, ...] = ()

    def __post_init__(self) -> None:
        if not all(
            isinstance(collection, tuple)
            for collection in (self.track_states, self.events, self.statistics)
        ):
            raise TypeError("counter collections must be immutable tuples")
        track_ids = tuple(item.track_id for item in self.track_states)
        if len(track_ids) != len(set(track_ids)):
            raise ValueError("counter state contains duplicate track IDs")
        statistic_keys = tuple(
            (direction, class_name) for direction, class_name, _ in self.statistics
        )
        if len(statistic_keys) != len(set(statistic_keys)):
            raise ValueError("counter state contains duplicate statistics")


def _crossing_direction(
    new_side: int,
    *,
    negative_to_positive: CrossingDirection,
    positive_to_negative: CrossingDirection,
) -> CrossingDirection:
    return negative_to_positive if new_side > 0 else positive_to_negative


def update_counter(
    state: CounterState,
    tracks: Sequence[TrackedObject],
    *,
    frame_index: int,
    frame_size: tuple[int, int],
    line_start: Point,
    line_end: Point,
    deadband: float,
    minimum_track_age: int,
    counted_classes: frozenset[str],
    negative_to_positive: CrossingDirection,
    positive_to_negative: CrossingDirection,
    stale_after: int,
) -> tuple[CounterState, tuple[CountEvent, ...]]:
    """Advance crossing state and return only events created by this frame."""

    height, width = frame_size
    if height <= 0 or width <= 0:
        raise ValueError("frame dimensions must be positive")
    if frame_index < 0:
        raise ValueError("frame_index must be non-negative")
    if minimum_track_age < 1 or stale_after < 0:
        raise ValueError("age and stale limits must be valid")
    if negative_to_positive is positive_to_negative:
        raise ValueError("crossing direction labels must be different")

    previous = {item.track_id: item for item in state.track_states}
    next_states: dict[int, TrackCrossingState] = {
        track_id: item
        for track_id, item in previous.items()
        if frame_index - item.last_seen_frame <= stale_after
    }
    counted = state.counted
    new_events: list[CountEvent] = []

    for track in tracks:
        if track.detection.class_name not in counted_classes or track.age < minimum_track_age:
            continue

        point = normalize_point(track.anchor, frame_size)
        side = line_side(point, line_start, line_end, deadband=deadband)
        prior = next_states.get(track.track_id)

        if prior is None:
            if side != 0:
                next_states[track.track_id] = TrackCrossingState(
                    track.track_id, side, point, frame_index
                )
            continue

        if side == 0:
            next_states[track.track_id] = TrackCrossingState(
                prior.track_id,
                prior.stable_side,
                prior.stable_point,
                frame_index,
            )
            continue

        if side != prior.stable_side and segments_intersect(
            prior.stable_point, point, line_start, line_end
        ):
            direction = _crossing_direction(
                side,
                negative_to_positive=negative_to_positive,
                positive_to_negative=positive_to_negative,
            )
            dedupe_key = (track.track_id, direction)
            if dedupe_key not in counted:
                counted = counted | {dedupe_key}
                new_events.append(
                    CountEvent(
                        track_id=track.track_id,
                        class_name=track.detection.class_name,
                        direction=direction,
                        frame_index=frame_index,
                    )
                )

        next_states[track.track_id] = TrackCrossingState(
            track.track_id,
            side,
            point,
            frame_index,
        )

    statistics = state.statistics
    if new_events:
        statistic_counts = {
            (direction, class_name): count for direction, class_name, count in state.statistics
        }
        for event in new_events:
            key = (event.direction, event.class_name)
            statistic_counts[key] = statistic_counts.get(key, 0) + 1
        statistics = tuple(
            sorted(
                (
                    (direction, class_name, count)
                    for (direction, class_name), count in statistic_counts.items()
                ),
                key=lambda item: (item[0].value, item[1]),
            )
        )

    next_state = CounterState(
        track_states=tuple(sorted(next_states.values(), key=lambda item: item.track_id)),
        counted=counted,
        events=state.events if not new_events else (*state.events, *new_events),
        statistics=statistics,
    )
    return next_state, tuple(new_events)
