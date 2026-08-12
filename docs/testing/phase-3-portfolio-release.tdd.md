# Phase 3 portfolio release - TDD evidence

## Scope and user journeys

This phase was derived from the approved Phase 3 plan after PR #1 merged into `main`. It is intentionally limited to a small, reproducible GitHub portfolio surface: no new model, tracker, API, UI, webcam, or deployment feature was added.

| User journey | Testable guarantee |
| --- | --- |
| As a recruiter, I can understand the project and see a real result in a few minutes. | The README has the required sections, all four CLI commands, a real evidence link, and a compact GIF. |
| As a reviewer, I can identify the demo source and its limits. | The GIF has a size and signature check; its attribution, checksum, frame range, and AI-assisted evaluation caveat are committed. |
| As a contributor, I can reproduce project checks without downloading model weights. | CI is present, pins its external actions, uses the lockfile, excludes opt-in model tests, and runs lint, types, coverage, and dependency audit. |

## RED to GREEN record

| Stage | Command | Observed result | What it proves |
| --- | --- | --- | --- |
| RED | `uv run --frozen pytest tests/repository/test_portfolio_contract.py -q` | `17 failed in 0.40s` | The old seven-line README and missing demo, provenance, license, and workflow did not meet the public portfolio contract. |
| RED checkpoint | `git commit` | `8142a37 test: define portfolio release contract` | The failing contract is preserved on `feat/03-portfolio-release` before implementation. |
| GREEN | `uv run --frozen pytest tests/repository/test_portfolio_contract.py -q` | `18 passed in 0.04s` | The completed README, demo, provenance, license, notices, and CI satisfy the repository-level contract. |

## Quality gates

All commands were run locally on Windows with Python 3.11.15 and the committed `uv.lock`.

| Gate | Command | Result |
| --- | --- | --- |
| Format | `uv run --frozen ruff format --check .` | PASS - 31 files already formatted |
| Lint | `uv run --frozen ruff check .` | PASS |
| Types | `uv run --frozen mypy src` | PASS - no issues in 11 source files |
| Tests and coverage | `uv run --frozen pytest -m "not model" --cov=traffic_analytics --cov-report=term-missing -q` | PASS - 107 passed, 1 model test deselected, 85.54% branch coverage |
| Dependency audit | `uv run --frozen pip-audit` | PASS - no known vulnerabilities; local `traffic-analytics` was skipped because it is not published on PyPI |
| Documentation links and CI parse | repository-local link and YAML check | PASS - 12 local links resolve; `quality` job exists |
| Secret-pattern scan | `rg` over changed public text and workflow files | PASS - no potential secret pattern found |

## Demo verification

- `examples/result.gif` uses inclusive frames 330-465 of the locally reviewed 30 FPS annotated derivative, sampled every third frame.
- Output: 46 frames, 4.6 seconds, 640 x 360, 5,168,836 bytes (under the 5 MiB contract limit of 5,242,880 bytes).
- SHA-256: `e9506431491e241ce518f65450062d791da130eafeff70b3fd0af8d3a2f2d336`.
- Visual review was performed on the first, middle, and final GIF frames. Bounding boxes, track IDs, trajectories, the counting line, directional totals, and FPS remain visible after downsampling.
- The source attribution and CC BY 3.0 derivative terms are in [examples/README.md](../../examples/README.md). The GIF is a visual demo only; the associated one-event window remains AI-assisted and is not a general accuracy claim.

## Review and known gaps

Code/security review of the Phase 3 diff found and corrected one non-blocking presentation issue: a mojibake dash in `THIRD_PARTY_NOTICES.md` was replaced with ASCII text. The final workflow has read-only `contents` permission, uses `pull_request` rather than `pull_request_target`, contains no secrets, and pins its three external actions to 40-character commit SHAs.

GitHub Actions has not run yet because this branch has not been pushed. Remote CI status must be checked after a future push and before merging the Phase 3 PR.
