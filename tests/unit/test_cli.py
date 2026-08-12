from __future__ import annotations

from pathlib import Path

import pytest

from traffic_analytics.cli import build_parser


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


def test_parser_rejects_unknown_mode() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["serve"])
