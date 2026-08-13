"""Repository-level contract for the Phase 4 visual documentation."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
README_PATH = PROJECT_ROOT / "README.md"
PHASE_2_EVIDENCE_PATH = PROJECT_ROOT / "docs" / "evidence" / "phase-2" / "phase-2-evidence.md"
EXAMPLES_README_PATH = PROJECT_ROOT / "examples" / "README.md"
ANNOTATIONS_README_PATH = PROJECT_ROOT / "data" / "annotations" / "README.md"
DIAGRAMS_PATH = PROJECT_ROOT / "docs" / "diagrams"


@pytest.mark.parametrize(
    ("svg_name", "source_name", "expected_labels"),
    [
        (
            "architecture.svg",
            "architecture.mmd",
            ("YOLO26", "ByteTrack", "Đếm qua vạch", "CSV sự kiện"),
        ),
        (
            "evaluation-provenance.svg",
            "evaluation-provenance.mmd",
            ("CC BY 3.0", "Có hỗ trợ AI", "Nhãn tham chiếu", "Độ chính xác"),
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
        assert label.casefold() in svg.casefold()
        assert label.casefold() in source.casefold()


@pytest.mark.parametrize("svg_name", ["architecture.svg", "evaluation-provenance.svg"])
def test_svg_diagrams_are_well_formed_and_keep_text_origins_on_canvas(svg_name: str) -> None:
    # SVG files here are committed repository assets, not untrusted input.
    root = ElementTree.parse(DIAGRAMS_PATH / svg_name).getroot()  # noqa: S314
    _, _, canvas_width, canvas_height = map(float, root.attrib["viewBox"].split())

    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    for text_element in root.findall(".//{http://www.w3.org/2000/svg}text"):
        x = float(text_element.attrib["x"])
        y = float(text_element.attrib["y"])

        assert 0 <= x <= canvas_width
        assert 0 <= y <= canvas_height


def test_architecture_svg_connects_the_counter_to_each_output_card() -> None:
    architecture_svg = (DIAGRAMS_PATH / "architecture.svg").read_text(encoding="utf-8")

    assert 'd="M1260 484 V522 H256 V622"' in architecture_svg
    assert 'd="M1326 484 V554 H694 V622"' in architecture_svg
    assert 'd="M1392 484 V586 H1132 V622"' in architecture_svg


def test_evaluation_svg_preserves_prediction_and_truth_topology() -> None:
    evaluation_svg = (DIAGRAMS_PATH / "evaluation-provenance.svg").read_text(encoding="utf-8")
    evaluation_mermaid = (DIAGRAMS_PATH / "evaluation-provenance.mmd").read_text(encoding="utf-8")

    for connector in (
        'd="M899 476 V542 H684 V570"',
        'd="M1256 476 V542 H1036 V570"',
        'd="M684 760 V786 H1212 V665 H1232"',
        'd="M1036 760 V786 H1212 V695 H1232"',
        'd="M1344 760 V802"',
        'd="M1092 877 H974"',
    ):
        assert connector in evaluation_svg

    assert "predictions --> matcher" in evaluation_mermaid
    assert "truth --> matcher" in evaluation_mermaid
    assert "matcher --> metrics" in evaluation_mermaid
    assert "metrics --> caveat" in evaluation_mermaid


def test_evaluation_diagram_labels_precision_and_recall_unambiguously() -> None:
    expected_labels = ("Precision (độ chính xác)", "Recall (độ thu hồi)")

    for path in (
        DIAGRAMS_PATH / "evaluation-provenance.svg",
        DIAGRAMS_PATH / "evaluation-provenance.mmd",
    ):
        diagram = path.read_text(encoding="utf-8")
        for label in expected_labels:
            assert label in diagram


def test_evaluation_svg_wraps_metric_and_caveat_copy_inside_their_cards() -> None:
    evaluation_svg = (DIAGRAMS_PATH / "evaluation-provenance.svg").read_text(encoding="utf-8")

    for text_line in (
        "Precision (độ chính xác) 0.20",
        "Recall (độ thu hồi) 1.00",
        "F1 0.333 • 1 TP, 4 FP, 0 FN",
        "Cần clip liên tục dài hơn, hai người gán nhãn độc lập và ghi nhận mức đồng thuận",
        "trước khi báo cáo độ chính xác tổng hợp.",
    ):
        assert text_line in evaluation_svg

    assert "Recall (độ thu hồi) 1.00 • F1 0.333" not in evaluation_svg


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
    annotations_readme = ANNOTATIONS_README_PATH.read_text(encoding="utf-8")

    assert "Từ video giao thông cục bộ" in readme
    assert "# Nguồn gốc của demo" in examples_readme
    assert "# Annotation sự kiện tạm thời" in annotations_readme
