# Bằng chứng giao thông thật Phase 2 — ghi nhận TDD

## Phạm vi và user journey

Không dùng file kế hoạch bên ngoài. Công việc Phase 2 được rút ra từ mục tiêu
đã thống nhất: tạo GitHub portfolio nhỏ nhưng đáng tin với evidence từ traffic
clip thật có license.

- Là một evaluator, tôi cần manual label dùng reviewer event ID ổn định thay
  vì ByteTrack ID do model sở hữu, để label vẫn hợp lệ khi tracker đổi hoặc
  chạy lại.
- Là một video reviewer, tôi cần output media từ chối FPS metadata vô lý, để
  WebM source không thể tạo review video bị tăng tốc không dùng được.
- Là một repository visitor, tôi cần source license, checksum, annotation
  scope, lệnh chính xác và limitation trung thực, để kết quả có thể kiểm tra
  mà không phải commit raw media hay model weights.

## Checkpoint RED → GREEN

| Hành vi | Bằng chứng RED | Bằng chứng GREEN | Checkpoint | Cam kết |
| --- | --- | --- | --- | --- |
| Annotation độc lập tracker | `uv run --frozen pytest tests/unit/test_evaluation.py -q` → collection error: thiếu `load_ground_truth_events_csv` | `uv run --frozen pytest tests/unit/test_evaluation.py tests/unit/test_cli.py -q` → **14 passed** | `1704ce3`, `e1ffc85`, `0255465` | Public evaluator nhận `event_id,frame_index,class_name,direction`; ID lỗi bị từ chối; prediction CSV tiếp tục yêu cầu `track_id`. |
| FPS video vô lý | `uv run --frozen pytest tests/integration/test_pipeline.py -q` → collection error: thiếu `_safe_output_fps` | Cùng lệnh sau implementation → **10 passed** | `789134a`, `1de3fd6` | Source FPS hữu hạn trong [1, 240] được giữ lại; 0, âm, NaN và 1,000 FPS dùng fallback 30 FPS. |

## Bằng chứng chạy với dữ liệu thật

- Source: `Street traffic.webm`, San Francisco, CC BY 3.0; raw video local và
  có checksum. Xem
  [`../evidence/phase-2/street_traffic.provenance.json`](../evidence/phase-2/street_traffic.provenance.json).
- Full local CPU run: 1,050 frame trong 79.7015 s (**13.17 FPS**), tạo 7
  predicted crossing event.
- Đánh giá lát cắt tạm thời có thể chạy lại:

  ```powershell
  uv run --frozen traffic-analytics evaluate `
    --predictions docs/evidence/phase-2/street_traffic-window-330-465.predictions.csv `
    --ground-truth data/annotations/street_traffic-window-330-465.v1.events.csv `
    --frame-tolerance 5
  ```

  Kết quả: 5 prediction, 1 annotation tạm thời có hỗ trợ AI, 1 TP, 4 FP,
  F1 0.33333333333333337. Đây không phải general accuracy claim.

## Xác minh cuối

```powershell
uv run --frozen ruff format --check .
uv run --frozen ruff check .
uv run --frozen mypy src
uv run --frozen pytest --cov=traffic_analytics --cov-report=term-missing -q
uv run --frozen pip-audit
```

Kết quả cuối:

- Ruff format: **27 files already formatted**.
- Ruff lint: **All checks passed**.
- Strict mypy: **Success: no issues found in 11 source files**.
- Tests: **83 passed, 1 skipped**; branch-aware coverage **85.07%** (tối thiểu
  80%). Test skipped là real-model smoke test opt-in có chủ ý.
- Dependency audit ban đầu tìm thấy `PYSEC-2026-1845` trong `pytest 8.4.2`.
  `pytest` được ràng buộc `>=9.0.3,<10`, resolve thành 9.1.1, và audit cuối
  báo cáo **No known vulnerabilities found**. Editable local package được bỏ
  qua vì không phát hành trên PyPI.

## Khoảng trống đã biết

- Annotation có hỗ trợ AI và chỉ phủ cửa sổ liên tục 4.53 giây. Cần review độc
  lập của con người trước khi báo cáo accuracy.
- Benchmark chỉ CPU và một scene. Nó không chứng minh real-time GPU deployment
  hay multi-camera generalization.
- Full artifact, raw media và weights giữ local theo thiết kế; hash, source URL
  và lệnh tái tạo được commit.
