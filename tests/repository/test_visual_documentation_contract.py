"""Repository-level contract for the Phase 4 visual documentation."""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
README_PATH = PROJECT_ROOT / "README.md"
PHASE_2_EVIDENCE_PATH = PROJECT_ROOT / "docs" / "evidence" / "phase-2" / "phase-2-evidence.md"
EXAMPLES_README_PATH = PROJECT_ROOT / "examples" / "README.md"
DIAGRAMS_PATH = PROJECT_ROOT / "docs" / "diagrams"


@pytest.mark.parametrize(
    ("svg_name", "source_name", "expected_labels"),
    [
        (
            "architecture.svg",
            "architecture.mmd",
            ("YOLO26", "ByteTrack", "Line crossing", "Event CSV"),
        ),
        (
            "evaluation-provenance.svg",
            "evaluation-provenance.mmd",
            ("CC BY 3.0", "AI-assisted", "Ground truth", "Precision"),
        ),
    ],
)
def test_diagrams_are_committed_as_svg_with_editable_mermaid_sources(
    svg_name: str, source_name: str, expected_labels: tuple[str, ...]
) -> None:
    svg_path = DIAGRAMS_PATH / svg_name
    source_path = DIAGRAMS_PATH / source_name

    assert svg_path.is_file()
    assert source_path.is_file()

    svg = svg_path.read_text(encoding="utf-8")
    source = source_path.read_text(encoding="utf-8")

    assert "<svg" in svg
    assert "viewBox=" in svg
    assert "flowchart" in source
    for label in expected_labels:
        assert label in svg
        assert label in source


def test_readme_uses_vietnamese_visual_architecture_documentation() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    assert "## Kiến trúc" in readme
    assert "docs/diagrams/architecture.svg" in readme
    assert "docs/diagrams/architecture.mmd" in readme
    assert "## Luồng bằng chứng và đánh giá" in readme
    assert "docs/diagrams/evaluation-provenance.svg" in readme


def test_phase_2_evidence_explains_provenance_with_the_visual_flow() -> None:
    evidence = PHASE_2_EVIDENCE_PATH.read_text(encoding="utf-8")

    assert "## Luồng provenance và đánh giá" in evidence
    assert "../../diagrams/evaluation-provenance.svg" in evidence
    assert "../../diagrams/evaluation-provenance.mmd" in evidence
    assert "không phải benchmark tổng quát" in evidence


def test_public_portfolio_documentation_is_vietnamese() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    examples_readme = EXAMPLES_README_PATH.read_text(encoding="utf-8")

    assert "Từ video giao thông cục bộ" in readme
    assert "# Nguồn gốc của demo" in examples_readme
