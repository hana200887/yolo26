from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import traffic_analytics.cli as cli
from traffic_analytics.cli import build_parser, main
from traffic_analytics.pipeline import PipelineMode


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


@pytest.mark.parametrize("command", ["detect", "track", "analyze"])
def test_video_command_dispatches_all_user_arguments(
    command: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    source = Path("traffic.mp4")
    config = SimpleNamespace(model=object(), tracking=object())
    calls: dict[str, object] = {}

    class Summary:
        def to_dict(self) -> dict[str, str]:
            return {"status": "ok"}

    def fake_run_video(video_source: Path, **kwargs: object) -> Summary:
        calls.update({"source": video_source, **kwargs})
        return Summary()

    monkeypatch.setattr(cli, "validate_video_source", lambda value: value)
    monkeypatch.setattr(cli, "load_config", lambda value: config)
    monkeypatch.setattr(cli, "UltralyticsAdapter", lambda model, tracking: object())
    monkeypatch.setattr(cli, "run_video", fake_run_video)

    exit_code = main([command, "--source", str(source), "--no-preview", "--max-frames", "7"])

    assert exit_code == 0
    assert calls["source"] == source
    assert calls["mode"] is PipelineMode(command)
    assert calls["config"] is config
    assert calls["adapter"] is not None
    assert calls["preview"] is False
    assert calls["max_frames"] == 7
    assert '"status": "ok"' in capsys.readouterr().out


def test_video_command_reports_output_io_errors(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config = SimpleNamespace(model=object(), tracking=object())

    def fail_run_video(*args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(cli, "validate_video_source", lambda value: value)
    monkeypatch.setattr(cli, "load_config", lambda value: config)
    monkeypatch.setattr(cli, "UltralyticsAdapter", lambda model, tracking: object())
    monkeypatch.setattr(cli, "run_video", fail_run_video)

    exit_code = main(["analyze", "--source", "traffic.mp4"])

    assert exit_code == 2
    assert "disk full" in capsys.readouterr().err
