from __future__ import annotations

from pathlib import Path

import pytest

from traffic_analytics.cli import build_parser, main


@pytest.mark.parametrize("command", ["detect", "track", "analyze"])
def test_video_commands_share_the_small_public_interface(command: str) -> None:
    args = build_parser().parse_args([command, "--source", "traffic.mp4", "--no-preview"])

    assert args.command == command
    assert args.source == Path("traffic.mp4")
    assert args.preview is False


def test_evaluate_command_requires_both_event_files() -> None:
    args = build_parser().parse_args(
        ["evaluate", "--predictions", "pred.csv", "--ground-truth", "truth.csv"]
    )

    assert args.predictions == Path("pred.csv")
    assert args.ground_truth == Path("truth.csv")


def test_evaluate_command_accepts_tracker_independent_ground_truth(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    predictions = tmp_path / "predictions.csv"
    predictions.write_text(
        "frame_index,track_id,class_name,direction\n42,19,bus,OUT\n",
        encoding="utf-8",
    )
    ground_truth = tmp_path / "ground-truth.csv"
    ground_truth.write_text(
        "event_id,frame_index,class_name,direction\n4,42,bus,OUT\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "evaluate",
            "--predictions",
            str(predictions),
            "--ground-truth",
            str(ground_truth),
        ]
    )

    assert exit_code == 0
    assert '"true_positives": 1' in capsys.readouterr().out


@pytest.mark.parametrize(
    ("event_id", "class_name", "message"),
    [
        ("01", "car", "duplicate event_id"),
        ("2", "buss", "invalid class_name"),
    ],
)
def test_evaluate_command_rejects_invalid_ground_truth(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    event_id: str,
    class_name: str,
    message: str,
) -> None:
    predictions = tmp_path / "predictions.csv"
    predictions.write_text(
        "frame_index,track_id,class_name,direction\n42,19,bus,OUT\n",
        encoding="utf-8",
    )
    ground_truth = tmp_path / "ground-truth.csv"
    ground_truth.write_text(
        f"event_id,frame_index,class_name,direction\n1,42,bus,OUT\n{event_id},43,{class_name},IN\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "evaluate",
            "--predictions",
            str(predictions),
            "--ground-truth",
            str(ground_truth),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert message in captured.err


def test_parser_rejects_unknown_mode() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["serve"])
