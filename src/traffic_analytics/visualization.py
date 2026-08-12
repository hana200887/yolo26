"""OpenCV rendering kept separate from inference and analytics state."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

import cv2
import numpy as np
from numpy.typing import NDArray

from traffic_analytics.config import AppConfig
from traffic_analytics.models import CountEvent, Detection, Point, TrackedObject

Frame = NDArray[np.uint8]
CLASS_COLORS: dict[str, tuple[int, int, int]] = {
    "person": (180, 180, 180),
    "bicycle": (255, 180, 0),
    "car": (40, 210, 80),
    "motorcycle": (0, 190, 255),
    "bus": (255, 100, 40),
    "truck": (180, 80, 255),
}


def _pixel(point: Point, frame: Frame) -> tuple[int, int]:
    height, width = frame.shape[:2]
    return round(point.x * width), round(point.y * height)


def _draw_detection(frame: Frame, detection: Detection, label: str) -> None:
    color = CLASS_COLORS.get(detection.class_name, (220, 220, 220))
    box = detection.bbox
    start, end = (round(box.x1), round(box.y1)), (round(box.x2), round(box.y2))
    cv2.rectangle(frame, start, end, color, 2)
    cv2.putText(
        frame,
        label,
        (start[0], max(18, start[1] - 6)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        color,
        1,
        cv2.LINE_AA,
    )


def render_frame(
    frame: Frame,
    *,
    detections: Sequence[Detection],
    tracks: Sequence[TrackedObject],
    all_events: Sequence[CountEvent],
    config: AppConfig,
    fps: float | None = None,
) -> Frame:
    """Return an annotated copy; the caller-owned input frame is untouched."""

    rendered = frame.copy()
    options = config.visualization
    visible_tracks = tuple(
        track for track in tracks if track.detection.confidence >= config.model.display_confidence
    )
    if visible_tracks and options.show_detections:
        for track in visible_tracks:
            identity = f" #{track.track_id}" if options.show_track_ids else ""
            label = (
                f"{track.detection.class_name}{identity} "
                f"{track.detection.confidence:.2f} {track.movement.value}"
            )
            _draw_detection(rendered, track.detection, label)
    elif options.show_detections:
        for detection in detections:
            if detection.confidence >= config.model.display_confidence:
                _draw_detection(
                    rendered,
                    detection,
                    f"{detection.class_name} {detection.confidence:.2f}",
                )

    if options.show_trajectories:
        for track in visible_tracks:
            if len(track.trajectory) >= 2:
                points = np.asarray(
                    [(round(point.x), round(point.y)) for point in track.trajectory],
                    dtype=np.int32,
                )
                cv2.polylines(
                    rendered,
                    [points.reshape((-1, 1, 2))],
                    False,
                    CLASS_COLORS.get(track.detection.class_name, (220, 220, 220)),
                    2,
                    cv2.LINE_AA,
                )

    if options.show_counting_line:
        line = config.counting.line
        cv2.line(
            rendered,
            _pixel(Point(*line.start), rendered),
            _pixel(Point(*line.end), rendered),
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )

    if options.show_statistics:
        counts = Counter((event.direction.value, event.class_name) for event in all_events)
        totals = Counter(event.direction.value for event in all_events)
        lines = [f"IN {totals['IN']}  OUT {totals['OUT']}"]
        lines.extend(
            f"{direction} {class_name}: {count}"
            for (direction, class_name), count in sorted(counts.items())
        )
        for index, text in enumerate(lines):
            cv2.putText(
                rendered,
                text,
                (12, 24 + index * 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

    if options.show_fps and fps is not None:
        cv2.putText(
            rendered,
            f"FPS {fps:.1f}",
            (12, rendered.shape[0] - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
    return rendered
