"""Small event-level evaluation harness for line-crossing analytics."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from traffic_analytics.models import CountEvent, CrossingDirection

MAX_EVENT_FILE_BYTES = 10_000_000
EVENT_FIELDS = ("frame_index", "track_id", "class_name", "direction")
GROUND_TRUTH_EVENT_FIELDS = ("event_id", "frame_index", "class_name", "direction")
EventKind = tuple[str, CrossingDirection]


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """Event-matching metrics for one evaluated video."""

    total_predictions: int
    total_ground_truth: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    absolute_count_error: int
    frame_tolerance: int

    def to_dict(self) -> dict[str, int | float]:
        """Return a JSON-serializable representation."""

        return asdict(self)


def _maximum_temporal_matches(
    predictions: Sequence[CountEvent],
    ground_truth: Sequence[CountEvent],
    *,
    frame_tolerance: int,
) -> int:
    """Return maximum cardinality matches for ordered points on the frame timeline."""

    prediction_groups: dict[EventKind, list[int]] = {}
    truth_groups: dict[EventKind, list[int]] = {}
    for prediction in predictions:
        prediction_groups.setdefault((prediction.class_name, prediction.direction), []).append(
            prediction.frame_index
        )
    for truth in ground_truth:
        truth_groups.setdefault((truth.class_name, truth.direction), []).append(truth.frame_index)

    matches = 0
    for event_kind in prediction_groups.keys() & truth_groups.keys():
        prediction_frames = sorted(prediction_groups[event_kind])
        truth_frames = sorted(truth_groups[event_kind])
        prediction_index = 0
        truth_index = 0
        while prediction_index < len(prediction_frames) and truth_index < len(truth_frames):
            prediction_frame = prediction_frames[prediction_index]
            truth_frame = truth_frames[truth_index]
            if prediction_frame < truth_frame - frame_tolerance:
                prediction_index += 1
            elif truth_frame < prediction_frame - frame_tolerance:
                truth_index += 1
            else:
                matches += 1
                prediction_index += 1
                truth_index += 1
    return matches


def evaluate_events(
    predictions: Sequence[CountEvent],
    ground_truth: Sequence[CountEvent],
    *,
    frame_tolerance: int,
) -> EvaluationReport:
    """Maximize one-to-one class/direction matches within a frame tolerance."""

    if frame_tolerance < 0:
        raise ValueError("frame tolerance must be non-negative")

    true_positives = _maximum_temporal_matches(
        predictions,
        ground_truth,
        frame_tolerance=frame_tolerance,
    )
    false_positives = len(predictions) - true_positives
    false_negatives = len(ground_truth) - true_positives
    precision = true_positives / len(predictions) if predictions else 0.0
    recall = true_positives / len(ground_truth) if ground_truth else 0.0
    f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
    return EvaluationReport(
        total_predictions=len(predictions),
        total_ground_truth=len(ground_truth),
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
        f1=f1,
        absolute_count_error=abs(len(predictions) - len(ground_truth)),
        frame_tolerance=frame_tolerance,
    )


def _load_event_rows(
    path: Path,
    *,
    fields: tuple[str, str, str, str],
    identifier_field: str,
    format_name: str,
) -> tuple[CountEvent, ...]:
    """Read a bounded event CSV and map its ID field to the internal event type."""

    event_path = path.resolve(strict=False)
    if not event_path.is_file():
        raise FileNotFoundError(event_path)
    if event_path.stat().st_size > MAX_EVENT_FILE_BYTES:
        raise ValueError("event file must not exceed 10 MB")
    events: list[CountEvent] = []
    try:
        with event_path.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames is None or not set(fields).issubset(reader.fieldnames):
                raise ValueError(f"{format_name} must contain: {', '.join(fields)}")
            for row_number, row in enumerate(reader, start=2):
                try:
                    events.append(
                        CountEvent(
                            track_id=int(row[identifier_field]),
                            class_name=row["class_name"],
                            direction=CrossingDirection(row["direction"]),
                            frame_index=int(row["frame_index"]),
                        )
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError(f"invalid event CSV row {row_number}") from exc
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ValueError(f"could not read event CSV: {event_path}") from exc
    return tuple(events)


def load_events_csv(path: Path) -> tuple[CountEvent, ...]:
    """Read tracker-generated event output with its ByteTrack ID."""

    return _load_event_rows(
        path,
        fields=EVENT_FIELDS,
        identifier_field="track_id",
        format_name="event CSV",
    )


def load_ground_truth_events_csv(path: Path) -> tuple[CountEvent, ...]:
    """Read manual event labels that use a human-assigned ID, not a tracker ID."""

    return _load_event_rows(
        path,
        fields=GROUND_TRUTH_EVENT_FIELDS,
        identifier_field="event_id",
        format_name="ground-truth CSV",
    )
