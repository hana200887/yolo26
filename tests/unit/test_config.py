from pathlib import Path
from shutil import copyfile

import pytest
import yaml
from pydantic import ValidationError

from traffic_analytics.config import AppConfig, load_config

ROOT = Path(__file__).parents[2]


def _default_payload() -> dict[str, object]:
    with (ROOT / "configs" / "default.yaml").open(encoding="utf-8") as stream:
        payload = yaml.safe_load(stream)
    assert isinstance(payload, dict)
    return payload


def _write_payload(tmp_path: Path, payload: dict[str, object], name: str = "invalid.yaml") -> Path:
    path = tmp_path / name
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    copyfile(ROOT / "configs" / "bytetrack.yaml", tmp_path / "bytetrack.yaml")
    return path


def test_default_config_is_valid_and_frozen() -> None:
    config = load_config(ROOT / "configs" / "default.yaml")

    assert config.model.weights == "yolo26n.pt"
    assert config.model.image_size == 640
    assert config.model.inference_confidence == pytest.approx(0.10)
    assert config.tracking.track_low_thresh == pytest.approx(0.10)
    assert "person" in config.model.tracked_classes
    assert "person" not in config.counting.counted_classes
    assert config.counting.line.start != config.counting.line.end

    with pytest.raises(ValidationError):
        config.model.device = "cpu"  # type: ignore[misc]


def test_config_rejects_unknown_keys(tmp_path: Path) -> None:
    payload = _default_payload()
    payload["surprise"] = True
    path = _write_payload(tmp_path, payload)

    with pytest.raises(ValueError, match="surprise"):
        load_config(path)


@pytest.mark.parametrize(
    ("section", "key", "value", "message"),
    [
        ("model", "inference_confidence", 0.2, "track_low_thresh"),
        ("tracking", "direction_window", 31, "trajectory_length"),
        ("counting", "deadband", -0.1, "deadband"),
    ],
)
def test_config_rejects_invalid_cross_field_values(
    tmp_path: Path,
    section: str,
    key: str,
    value: object,
    message: str,
) -> None:
    payload = _default_payload()
    section_payload = payload[section]
    assert isinstance(section_payload, dict)
    section_payload[key] = value
    path = _write_payload(tmp_path, payload)

    with pytest.raises(ValueError, match=message):
        load_config(path)


def test_config_rejects_degenerate_or_out_of_bounds_line(tmp_path: Path) -> None:
    for points in (((0.5, 0.5), (0.5, 0.5)), ((-0.1, 0.5), (0.8, 0.5))):
        payload = _default_payload()
        counting = payload["counting"]
        assert isinstance(counting, dict)
        line = counting["line"]
        assert isinstance(line, dict)
        line["start"], line["end"] = points
        path = _write_payload(tmp_path, payload, "invalid-line.yaml")

        with pytest.raises(ValueError, match="line"):
            load_config(path)


def test_counted_classes_must_be_tracked(tmp_path: Path) -> None:
    payload = _default_payload()
    counting = payload["counting"]
    assert isinstance(counting, dict)
    counting["counted_classes"] = ["car", "airplane"]
    path = _write_payload(tmp_path, payload, "invalid-classes.yaml")

    with pytest.raises(ValueError, match="counted_classes"):
        load_config(path)


def test_load_config_rejects_missing_or_oversized_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "missing.yaml")

    path = tmp_path / "large.yaml"
    path.write_text("x" * (1_000_001), encoding="utf-8")

    with pytest.raises(ValueError, match="1 MB"):
        load_config(path)


def test_app_config_rejects_non_mapping_yaml(tmp_path: Path) -> None:
    path = tmp_path / "list.yaml"
    path.write_text("- not\n- a\n- mapping\n", encoding="utf-8")

    with pytest.raises(ValueError, match="mapping"):
        load_config(path)

    assert issubclass(AppConfig, object)
