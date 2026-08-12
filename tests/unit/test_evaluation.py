from __future__ import annotations

from pathlib import Path

import pytest

from traffic_analytics.evaluation import (
    evaluate_events,
    load_events_csv,
    load_ground_truth_events_csv,
)
from traffic_analytics.models import CountEvent, CrossingDirection


def _event(frame: int, *, track_id: int = 1, class_name: str = "car") -> CountEvent:
    return CountEvent(track_id, class_name, CrossingDirection.IN, frame)


def test_event_evaluation_matches_once_within_frame_tolerance() -> None:
    truth = (_event(10), _event(20, track_id=2))
    predictions = (_event(11, track_id=101), _event(12, track_id=102))

    report = evaluate_events(predictions, truth, frame_tolerance=2)

    assert report.true_positives == 1
    assert report.false_positives == 1
    assert report.false_negatives == 1
    assert report.precision == pytest.approx(0.5)
    assert report.recall == pytest.approx(0.5)
    assert report.f1 == pytest.approx(0.5)
    assert report.absolute_count_error == 0


def test_event_evaluation_maximizes_matches_instead_of_nearest_pair_greediness() -> None:
    predictions = (_event(11, track_id=1), _event(9, track_id=2))
    ground_truth = (_event(10, track_id=11), _event(13, track_id=12))

    report = evaluate_events(predictions, ground_truth, frame_tolerance=2)

    assert report.true_positives == 2
    assert report.false_positives == 0
    assert report.false_negatives == 0
    assert report.f1 == pytest.approx(1.0)


def test_event_evaluation_requires_same_class_and_direction() -> None:
    predictions = (
        _event(10, class_name="bus"),
        CountEvent(2, "car", CrossingDirection.OUT, 10),
    )

    report = evaluate_events(predictions, (_event(10),), frame_tolerance=0)

    assert report.true_positives == 0
    assert report.false_positives == 2
    assert report.false_negatives == 1
    assert report.f1 == 0.0
    assert report.absolute_count_error == 1


def test_event_evaluation_handles_empty_inputs_without_division_by_zero() -> None:
    report = evaluate_events((), (), frame_tolerance=0)

    assert report.precision == 0.0
    assert report.recall == 0.0
    assert report.f1 == 0.0
    assert report.absolute_count_error == 0


def test_event_evaluation_rejects_negative_tolerance() -> None:
    with pytest.raises(ValueError, match="tolerance"):
        evaluate_events((), (), frame_tolerance=-1)


def test_event_csv_loader_validates_schema_and_rows(tmp_path: Path) -> None:
    invalid_schema = tmp_path / "invalid-schema.csv"
    invalid_schema.write_text("frame,kind\n1,car\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must contain"):
        load_events_csv(invalid_schema)

    invalid_row = tmp_path / "invalid-row.csv"
    invalid_row.write_text(
        "frame_index,track_id,class_name,direction\n0,1,car,SIDEWAYS\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="row 2"):
        load_events_csv(invalid_row)


def test_ground_truth_loader_uses_human_annotation_schema(tmp_path: Path) -> None:
    annotations = tmp_path / "ground-truth.csv"
    annotations.write_text(
        "event_id,frame_index,class_name,direction\n"
        "7,42,bus,OUT\n",
        encoding="utf-8",
    )

    events = load_ground_truth_events_csv(annotations)

    assert events == (CountEvent(7, "bus", CrossingDirection.OUT, 42),)


def test_ground_truth_loader_rejects_invalid_event_id(tmp_path: Path) -> None:
    annotations = tmp_path / "ground-truth.csv"
    annotations.write_text(
        "event_id,frame_index,class_name,direction\n"
        "0,42,bus,OUT\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="row 2"):
        load_ground_truth_events_csv(annotations)
