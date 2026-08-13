"""Command-line interface for the compact traffic analytics project."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from importlib.resources import files
from pathlib import Path

from traffic_analytics.config import AppConfig, load_config
from traffic_analytics.evaluation import (
    evaluate_events,
    load_events_csv,
    load_ground_truth_events_csv,
)
from traffic_analytics.pipeline import PipelineMode, run_video, validate_video_source
from traffic_analytics.ultralytics_adapter import UltralyticsAdapter

DEFAULT_CONFIG = Path(str(files("traffic_analytics").joinpath("resources/default.yaml")))


def _load_cli_config(path: Path) -> AppConfig:
    """Load a config and keep packaged defaults independent of site-packages."""

    config = load_config(path)
    if path != DEFAULT_CONFIG:
        return config
    return config.model_copy(
        update={
            "video": config.video.model_copy(update={"output_dir": Path.cwd() / "data" / "outputs"})
        }
    )


def build_parser() -> argparse.ArgumentParser:
    """Create the four-command public CLI."""

    parser = argparse.ArgumentParser(
        prog="traffic-analytics",
        description="YOLO26 + ByteTrack traffic analytics for local videos.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("detect", "track", "analyze"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--source", type=Path, required=True)
        subparser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
        preview = subparser.add_mutually_exclusive_group()
        preview.add_argument("--preview", action="store_true", dest="preview")
        preview.add_argument("--no-preview", action="store_false", dest="preview")
        subparser.set_defaults(preview=None)
        subparser.add_argument("--max-frames", type=int)

    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("--predictions", type=Path, required=True)
    evaluate.add_argument("--ground-truth", type=Path, required=True)
    evaluate.add_argument("--frame-tolerance", type=int, default=5)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the selected command and return a process exit status."""

    args = build_parser().parse_args(argv)
    try:
        if args.command == "evaluate":
            report = evaluate_events(
                load_events_csv(args.predictions),
                load_ground_truth_events_csv(args.ground_truth),
                frame_tolerance=args.frame_tolerance,
            )
            print(json.dumps(report.to_dict(), indent=2))
            return 0

        source = validate_video_source(args.source)
        config = _load_cli_config(args.config)
        adapter = UltralyticsAdapter(config.model, config.tracking)
        summary = run_video(
            source,
            mode=PipelineMode(args.command),
            config=config,
            adapter=adapter,
            preview=args.preview,
            max_frames=args.max_frames,
        )
        print(json.dumps(summary.to_dict(), indent=2))
        return 0
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
