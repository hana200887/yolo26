"""Pure geometry helpers for normalized directional line crossing."""

from __future__ import annotations

from math import hypot

from traffic_analytics.models import Point

MINIMUM_LINE_LENGTH = 1e-9


def normalize_point(point: Point, frame_size: tuple[int, int]) -> Point:
    """Convert a pixel point to normalized coordinates using ``(height, width)``."""

    height, width = frame_size
    if height <= 0 or width <= 0:
        raise ValueError("frame dimensions must be positive")
    return Point(point.x / width, point.y / height)


def signed_distance_to_line(point: Point, start: Point, end: Point) -> float:
    """Return signed perpendicular distance from a point to a directed line."""

    delta_x = end.x - start.x
    delta_y = end.y - start.y
    length = hypot(delta_x, delta_y)
    if length <= MINIMUM_LINE_LENGTH:
        raise ValueError("line endpoints must be different")
    cross_product = delta_x * (point.y - start.y) - delta_y * (point.x - start.x)
    return cross_product / length


def line_side(point: Point, start: Point, end: Point, *, deadband: float) -> int:
    """Classify a point as negative, neutral, or positive relative to a line."""

    if deadband < 0.0:
        raise ValueError("deadband must be non-negative")
    distance = signed_distance_to_line(point, start, end)
    if abs(distance) <= deadband:
        return 0
    return 1 if distance > 0.0 else -1


def _orientation(first: Point, second: Point, third: Point) -> float:
    return (second.x - first.x) * (third.y - first.y) - (second.y - first.y) * (third.x - first.x)


def _on_segment(first: Point, point: Point, second: Point) -> bool:
    return (
        min(first.x, second.x) - MINIMUM_LINE_LENGTH
        <= point.x
        <= max(first.x, second.x) + MINIMUM_LINE_LENGTH
        and min(first.y, second.y) - MINIMUM_LINE_LENGTH
        <= point.y
        <= max(first.y, second.y) + MINIMUM_LINE_LENGTH
    )


def segments_intersect(
    first_start: Point,
    first_end: Point,
    second_start: Point,
    second_end: Point,
) -> bool:
    """Return whether two finite line segments intersect, including endpoints."""

    o1 = _orientation(first_start, first_end, second_start)
    o2 = _orientation(first_start, first_end, second_end)
    o3 = _orientation(second_start, second_end, first_start)
    o4 = _orientation(second_start, second_end, first_end)

    if (
        (o1 > MINIMUM_LINE_LENGTH and o2 < -MINIMUM_LINE_LENGTH)
        or (o1 < -MINIMUM_LINE_LENGTH and o2 > MINIMUM_LINE_LENGTH)
    ) and (
        (o3 > MINIMUM_LINE_LENGTH and o4 < -MINIMUM_LINE_LENGTH)
        or (o3 < -MINIMUM_LINE_LENGTH and o4 > MINIMUM_LINE_LENGTH)
    ):
        return True

    collinear_cases = (
        (o1, second_start, first_start, first_end),
        (o2, second_end, first_start, first_end),
        (o3, first_start, second_start, second_end),
        (o4, first_end, second_start, second_end),
    )
    return any(
        abs(value) <= MINIMUM_LINE_LENGTH and _on_segment(start, point, end)
        for value, point, start, end in collinear_cases
    )
