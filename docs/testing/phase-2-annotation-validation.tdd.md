# Phase 2.1 annotation validation â€” TDD record

## Scope and user journeys

No external plan file was used. This focused follow-up closes two review
findings on the ground-truth CSV boundary.

- As an evaluator, I need every reviewer-assigned event ID to be unique, so a
  duplicate row cannot silently distort event-level precision and recall.
- As an annotator, I need a typo in `class_name` rejected before evaluation, so
  metrics are not reported against a label outside the published taxonomy.
- As a reviewer, I need the CSV header to be unambiguous, so duplicate or
  undocumented fields cannot be silently reinterpreted by the CSV parser.

## RED â†’ GREEN checkpoints

| Behavior | RED evidence | GREEN evidence | Checkpoints | Guarantee |
| --- | --- | --- | --- | --- |
| Duplicate ground-truth IDs | `uv run --frozen pytest tests/unit/test_evaluation.py -q` â†’ **2 failed, 8 passed**; duplicate numeric IDs `1` and `01` were accepted | Same command â†’ **10 passed**; loader and CLI integration tests â†’ **18 passed** | `e945167`, `bc20693` | Parsed ground-truth `event_id` values must be unique, including equivalent integer spellings. |
| Published vehicle taxonomy | Same RED command â†’ `buss` was accepted | Same GREEN command â†’ **10 passed**; loader and CLI integration tests â†’ **18 passed** | `e945167`, `bc20693` | Ground truth accepts only `bicycle`, `car`, `motorcycle`, `bus`, and `truck`. |
| Unambiguous schema and canonical taxonomy | `uv run --frozen pytest tests/unit/test_evaluation.py -q` â†’ **2 failed, 10 passed**; duplicate headers and a second hard-coded class set remained | `uv run --frozen pytest tests/unit/test_evaluation.py tests/unit/test_config.py tests/unit/test_cli.py -q` â†’ **29 passed** | `78ae1b7`, `bc20693` | The header must exactly equal the four published fields, and evaluation reuses the one vehicle taxonomy from configuration. |

## Final verification

```powershell
uv run --frozen ruff format --check .
uv run --frozen ruff check .
uv run --frozen mypy src
uv run --frozen pytest --cov=traffic_analytics --cov-report=term-missing -q
uv run --frozen pip-audit
```

Results:

- Ruff format: **28 files already formatted**.
- Ruff lint: **All checks passed**.
- Strict mypy: **Success: no issues found in 11 source files**.
- Tests: **89 passed, 1 skipped**; branch-aware coverage **85.54%** (minimum
  80%). The skipped test remains the deliberately opt-in real-model smoke
  test.
- Dependency audit: **No known vulnerabilities found**. The editable local
  package is skipped because it is not published on PyPI.

## Scope limits

- Prediction CSV remains intentionally unrestricted by this annotation-only
  taxonomy check; model configuration already governs emitted prediction
  classes.
- Existing source media, pilot annotation data, and prediction evidence are not
  rewritten in this hardening change.
