"""Repository-level contracts for the public Phase 3 portfolio surface."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
README_PATH = PROJECT_ROOT / "README.md"
EXAMPLES_PATH = PROJECT_ROOT / "examples"
DEMO_GIF_PATH = EXAMPLES_PATH / "result.gif"
EXAMPLES_README_PATH = EXAMPLES_PATH / "README.md"
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
MAX_DEMO_GIF_BYTES = 5 * 1024 * 1024


@pytest.mark.parametrize(
    "heading",
    [
        "Demo",
        "Kiến trúc",
        "Cách hoạt động",
        "Cài đặt",
        "Cách dùng",
        "Kết quả",
        "Giới hạn",
        "Hướng phát triển",
    ],
)
def test_readme_has_recruiter_facing_sections(heading: str) -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    assert f"## {heading}" in readme


@pytest.mark.parametrize("command", ["detect", "track", "analyze", "evaluate"])
def test_readme_documents_each_public_cli_command(command: str) -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    assert f"traffic-analytics {command}" in readme


def test_readme_links_to_committed_real_traffic_evidence() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    assert "docs/evidence/phase-2/phase-2-evidence.md" in readme


def test_demo_gif_is_small_and_has_a_gif_signature() -> None:
    assert DEMO_GIF_PATH.is_file()
    assert DEMO_GIF_PATH.stat().st_size <= MAX_DEMO_GIF_BYTES
    assert DEMO_GIF_PATH.read_bytes().startswith((b"GIF87a", b"GIF89a"))


def test_demo_provenance_records_source_and_derivative_limits() -> None:
    provenance = EXAMPLES_README_PATH.read_text(encoding="utf-8")

    assert "https://commons.wikimedia.org/wiki/File:Street_traffic.webm" in provenance
    assert "CC BY 3.0" in provenance
    assert "có hỗ trợ AI" in provenance
    assert "không commit" in provenance


def test_repository_has_code_license_and_third_party_notices() -> None:
    license_text = (PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8")
    notices = (PROJECT_ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")

    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in license_text
    assert "Ultralytics" in notices
    assert "CC BY 3.0" in notices


def test_ci_runs_reproducible_non_model_quality_gates() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "uv sync --frozen" in workflow
    assert "ruff format --check" in workflow
    assert "ruff check" in workflow
    assert "mypy src" in workflow
    assert 'pytest -m "not model"' in workflow
    assert "pip-audit" in workflow


def test_ci_pins_external_actions_to_full_commit_shas() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    action_references = re.findall(r"^\s*- uses: [^@\s]+@([0-9a-f]{40})", workflow, re.MULTILINE)

    assert len(action_references) == 3
