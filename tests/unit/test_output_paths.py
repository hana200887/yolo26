from pathlib import Path

from traffic_analytics.pipeline import PipelineMode, _artifact_path, _unique_output_base


def test_artifact_path_preserves_dotted_source_stem() -> None:
    base = Path("outputs") / "street.v1-analyze"

    assert _artifact_path(base, ".mp4") == Path("outputs") / "street.v1-analyze.mp4"
    assert _artifact_path(base, ".events.csv") == Path("outputs") / "street.v1-analyze.events.csv"


def test_output_base_advances_without_reusing_existing_dotted_artifact(tmp_path: Path) -> None:
    source = tmp_path / "street.v1.mp4"
    source.touch()
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    (output_dir / "street.v1-analyze.mp4").touch()

    output_base = _unique_output_base(output_dir, source, PipelineMode.ANALYZE)

    assert output_base == output_dir / "street.v1-analyze-1"
