from pathlib import Path

import pytest

from traffic_analytics.pipeline import (
    PipelineMode,
    _artifact_path,
    _publish_artifact,
    _reserve_output_base,
    _unique_output_base,
)


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


def test_concurrent_reservations_use_distinct_output_bases(tmp_path: Path) -> None:
    source = tmp_path / "input.mp4"
    source.touch()
    output_dir = tmp_path / "outputs"

    first_base, first_reservation = _reserve_output_base(output_dir, source, PipelineMode.ANALYZE)
    second_base, second_reservation = _reserve_output_base(output_dir, source, PipelineMode.ANALYZE)

    assert first_base == output_dir / "input-analyze"
    assert second_base == output_dir / "input-analyze-1"
    assert first_reservation.is_file()
    assert second_reservation.is_file()


def test_publish_refuses_to_replace_an_artifact_created_by_another_run(tmp_path: Path) -> None:
    temporary = tmp_path / "temporary.mp4"
    final = tmp_path / "final.mp4"
    temporary.write_bytes(b"new output")
    final.write_bytes(b"existing output")

    with pytest.raises(FileExistsError, match="overwrite"):
        _publish_artifact(temporary, final)

    assert temporary.read_bytes() == b"new output"
    assert final.read_bytes() == b"existing output"


def test_publish_rolls_back_linked_artifact_when_temporary_cleanup_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    temporary = tmp_path / "temporary.mp4"
    final = tmp_path / "final.mp4"
    temporary.write_bytes(b"new output")
    unlink = Path.unlink

    def fail_temporary_cleanup(path: Path, *args: object, **kwargs: object) -> None:
        if path == temporary:
            raise OSError("intentional temporary cleanup failure")
        unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_temporary_cleanup)

    with pytest.raises(OSError, match="temporary cleanup"):
        _publish_artifact(temporary, final)

    assert final.exists() is False
