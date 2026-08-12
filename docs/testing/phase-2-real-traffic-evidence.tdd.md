# Phase 2 real-traffic evidence — TDD record

## Scope and user journeys

No external plan file was used. The Phase 2 work was derived from the agreed
goal of producing a small but credible GitHub portfolio project with evidence
from a real, licensed traffic clip.

- As an evaluator, I need manual labels to use a stable reviewer event ID rather
  than a model-owned ByteTrack ID, so labels remain valid when a tracker is
  changed or rerun.
- As a video reviewer, I need output media to reject implausible FPS metadata,
  so a WebM source cannot produce an unusably accelerated review video.
- As a repository visitor, I need source license, checksums, annotation scope,
  exact commands, and honest limitations, so the result can be inspected
  without committing raw media or model weights.

## RED → GREEN checkpoints

| Behavior | RED evidence | GREEN evidence | Checkpoints | Guarantee |
| --- | --- | --- | --- | --- |
| Tracker-independent annotations | `uv run --frozen pytest tests/unit/test_evaluation.py -q` → collection error: missing `load_ground_truth_events_csv` | `uv run --frozen pytest tests/unit/test_evaluation.py tests/unit/test_cli.py -q` → **14 passed** | `1704ce3`, `e1ffc85`, `0255465` | The public evaluator accepts `event_id,frame_index,class_name,direction`; malformed IDs are rejected; prediction CSV continues to require `track_id`. |
| Implausible video FPS | `uv run --frozen pytest tests/integration/test_pipeline.py -q` → collection error: missing `_safe_output_fps` | Same command after implementation → **10 passed** | `789134a`, `1de3fd6` | A finite source FPS in [1, 240] is preserved; zero, negative, NaN, and 1,000 FPS use the 30 FPS fallback. |

## Real-data execution evidence

- Source: `Street traffic.webm`, San Francisco, CC BY 3.0; raw video is local
  and checksummed. See
  [`../evidence/phase-2/street_traffic.provenance.json`](../evidence/phase-2/street_traffic.provenance.json).
- Full local CPU run: 1,050 frames in 79.7015 s (**13.17 FPS**), yielding 7
  predicted crossing events.
- Reproducible provisional slice evaluation:

  ```powershell
  uv run --frozen traffic-analytics evaluate `
    --predictions docs/evidence/phase-2/street_traffic-window-330-465.predictions.csv `
    --ground-truth data/annotations/street_traffic-window-330-465.v1.events.csv `
    --frame-tolerance 5
  ```

  Result: 5 predictions, 1 provisional AI-assisted annotation, 1 TP, 4 FP,
  F1 0.33333333333333337. This is not a general accuracy claim.

## Final verification

```powershell
uv run --frozen ruff format --check .
uv run --frozen ruff check .
uv run --frozen mypy src
uv run --frozen pytest --cov=traffic_analytics --cov-report=term-missing -q
uv run --frozen pip-audit
```

Final results:

- Ruff format: **27 files already formatted**.
- Ruff lint: **All checks passed**.
- Strict mypy: **Success: no issues found in 11 source files**.
- Tests: **83 passed, 1 skipped**; branch-aware coverage **85.07%** (minimum
  80%). The skipped test is the deliberately opt-in real-model smoke test.
- Dependency audit initially found `PYSEC-2026-1845` in `pytest 8.4.2`.
  `pytest` was constrained to `>=9.0.3,<10`, resolved to 9.1.1, and the final
  audit reported **No known vulnerabilities found**. The editable local package
  is naturally skipped because it is not published on PyPI.

## Known gaps

- The annotation is AI-assisted and only covers a continuous 4.53-second
  window. It requires independent human review before reporting accuracy.
- The benchmark is CPU-only and single-scene. It does not demonstrate
  real-time GPU deployment or multi-camera generalization.
- Full artifacts, raw media, and weights remain local by design; their hashes,
  source URL, and regeneration commands are committed instead.
