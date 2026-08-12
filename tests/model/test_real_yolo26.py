from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from traffic_analytics.config import load_config
from traffic_analytics.ultralytics_adapter import UltralyticsAdapter

ROOT = Path(__file__).parents[2]
RUN_MODEL_TESTS = os.environ.get("RUN_MODEL_TESTS") == "1"

pytestmark = [
    pytest.mark.model,
    pytest.mark.skipif(not RUN_MODEL_TESTS, reason="set RUN_MODEL_TESTS=1 for real weights"),
]


def test_official_yolo26_weights_support_project_predict_and_track_contracts() -> None:
    config = load_config(ROOT / "configs" / "default.yaml")
    adapter = UltralyticsAdapter(config.model, config.tracking)
    frame = np.zeros((640, 640, 3), dtype=np.uint8)

    detections = adapter.detect(frame)
    tracks = adapter.track(frame)

    assert isinstance(detections, tuple)
    assert isinstance(tracks, tuple)
