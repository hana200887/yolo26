# Phase 1 review fixes — TDD evidence

## Scope and journeys

This report covers the three actionable findings from the Phase 1 defect-first
review. No external plan file was used.

- As an evaluator, I need event matching to maximize valid one-to-one matches
  within the configured frame tolerance, so reported precision, recall, and F1
  do not depend on input order.
- As a traffic analyst, I need an identity that briefly disappears to preserve
  its age within the ByteTrack buffer, so a returning vehicle is not rejected by
  the minimum-age counting guard.
- As a video user, I need failed runs to leave no final output artifacts, so a
  partial video cannot be mistaken for a completed analysis.

## RED → GREEN record

| Behavior | RED evidence | GREEN evidence | Guarantee |
| --- | --- | --- | --- |
| Maximum-cardinality evaluation matching | `uv run --frozen pytest tests/unit/test_evaluation.py tests/integration/test_ultralytics_adapter.py tests/e2e/test_local_video_flow.py -q` → 3 failed, including TP `1` instead of `2` | Same command after fixes → 19 passed | Events are grouped by class/direction, sorted by frame, and matched one-to-one to maximize the number of in-tolerance pairs. |
| Track age survives a short unconfirmed gap and expires after buffer | Same RED command → returning ID had age `1` instead of `3` | Same command after fixes → 19 passed | Per-ID age/last-seen state is retained up to `track_buffer`, then pruned. |
| Failed run does not expose incomplete files | Same RED command → `.mp4` remained in output directory | Same command after fixes → 19 passed | Video, events, and summary use same-directory temporary paths; failures close the writer and remove current-run temporary/published artifacts. |
| Late event-write failure does not expose video | Added regression test after the atomic-output refactor | `uv run --frozen pytest tests/e2e/test_local_video_flow.py tests/unit/test_evaluation.py tests/integration/test_ultralytics_adapter.py -q` → 20 passed | Artifacts are published only after event CSV and summary generation both succeed. |

## Final verification

```powershell
uv run --frozen ruff format --check .
uv run --frozen ruff check .
uv run --frozen mypy src
uv run --frozen pytest --cov=traffic_analytics --cov-report=term-missing -q
```

Result: Ruff and strict mypy passed; **74 passed, 1 skipped**; total branch-aware
coverage was **84.07%** (minimum 80%).

## Known gaps

- The real model test remains opt-in (`RUN_MODEL_TESTS=1`) because it may load
  local weights and has already been smoke-tested separately in this workspace.
- Phase 2 will add an appropriately licensed traffic clip, manual ground truth,
  visual review, and measured performance evidence.
- Git checkpoint commits were not created because this checkout has no configured
  Git author identity; no identity was invented.
