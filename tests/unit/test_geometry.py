import pytest

from traffic_analytics.geometry import (
    line_side,
    normalize_point,
    segments_intersect,
    signed_distance_to_line,
)
from traffic_analytics.models import Point


def test_normalize_point_uses_width_and_height() -> None:
    assert normalize_point(Point(320.0, 360.0), (720, 1280)) == Point(0.25, 0.5)


@pytest.mark.parametrize("frame_size", [(0, 100), (100, 0), (-1, 100)])
def test_normalize_point_rejects_invalid_frame_size(frame_size: tuple[int, int]) -> None:
    with pytest.raises(ValueError, match="frame"):
        normalize_point(Point(1.0, 1.0), frame_size)


def test_signed_distance_and_side_follow_directed_line_orientation() -> None:
    start = Point(0.0, 0.5)
    end = Point(1.0, 0.5)

    assert signed_distance_to_line(Point(0.5, 0.25), start, end) == pytest.approx(-0.25)
    assert signed_distance_to_line(Point(0.5, 0.75), start, end) == pytest.approx(0.25)
    assert line_side(Point(0.5, 0.495), start, end, deadband=0.01) == 0
    assert line_side(Point(0.5, 0.25), start, end, deadband=0.01) == -1
    assert line_side(Point(0.5, 0.75), start, end, deadband=0.01) == 1


def test_signed_distance_rejects_degenerate_line() -> None:
    with pytest.raises(ValueError, match="line"):
        signed_distance_to_line(Point(0.5, 0.5), Point(0.2, 0.2), Point(0.2, 0.2))


@pytest.mark.parametrize(
    ("path_start", "path_end", "expected"),
    [
        (Point(0.5, 0.25), Point(0.5, 0.75), True),
        (Point(0.0, 0.25), Point(0.0, 0.75), False),
        (Point(0.5, 0.25), Point(0.5, 0.5), True),
        (Point(0.2, 0.25), Point(0.8, 0.25), False),
    ],
)
def test_segment_intersection_is_limited_to_finite_segments(
    path_start: Point,
    path_end: Point,
    expected: bool,
) -> None:
    assert segments_intersect(path_start, path_end, Point(0.25, 0.5), Point(0.75, 0.5)) is expected
