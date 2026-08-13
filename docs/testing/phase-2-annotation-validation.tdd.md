# Xác thực annotation Phase 2.1 — ghi nhận TDD

## Phạm vi và user journey

Không dùng file kế hoạch bên ngoài. Follow-up tập trung này đóng hai phát hiện
review ở CSV ground-truth boundary.

- Là một evaluator, tôi cần mỗi event ID do reviewer gán là duy nhất, để row
  trùng không âm thầm làm sai precision và recall ở mức sự kiện.
- Là một annotator, tôi cần lỗi gõ trong `class_name` bị từ chối trước khi
  đánh giá, để metric không báo cáo với nhãn ngoài taxonomy công bố.
- Là một reviewer, tôi cần CSV header không mơ hồ, để field trùng hay không có
  tài liệu không bị CSV parser diễn giải lại im lặng.

## Checkpoint RED → GREEN

| Hành vi | Bằng chứng RED | Bằng chứng GREEN | Checkpoint | Cam kết |
| --- | --- | --- | --- | --- |
| Ground-truth ID trùng | `uv run --frozen pytest tests/unit/test_evaluation.py -q` → **2 failed, 8 passed**; ID số `1` và `01` bị chấp nhận | Cùng lệnh → **10 passed**; loader và CLI integration test → **18 passed** | `e945167`, `bc20693` | `event_id` ground-truth sau parse phải duy nhất, kể cả cách viết số tương đương. |
| Taxonomy vehicle đã công bố | Cùng lệnh RED → `buss` bị chấp nhận | Cùng lệnh GREEN → **10 passed**; loader và CLI integration test → **18 passed** | `e945167`, `bc20693` | Ground truth chỉ nhận `bicycle`, `car`, `motorcycle`, `bus`, `truck`. |
| Schema rõ ràng và taxonomy chuẩn | `uv run --frozen pytest tests/unit/test_evaluation.py -q` → **2 failed, 10 passed**; header trùng và class set hard-code thứ hai còn tồn tại | `uv run --frozen pytest tests/unit/test_evaluation.py tests/unit/test_config.py tests/unit/test_cli.py -q` → **29 passed** | `78ae1b7`, `bc20693` | Header phải bằng đúng bốn field đã công bố; evaluation dùng chung vehicle taxonomy từ configuration. |

## Xác minh cuối

```powershell
uv run --frozen ruff format --check .
uv run --frozen ruff check .
uv run --frozen mypy src
uv run --frozen pytest --cov=traffic_analytics --cov-report=term-missing -q
uv run --frozen pip-audit
```

Kết quả:

- Ruff format: **28 files already formatted**.
- Ruff lint: **All checks passed**.
- Strict mypy: **Success: no issues found in 11 source files**.
- Tests: **89 passed, 1 skipped**; branch-aware coverage **85.54%** (tối thiểu
  80%). Test skipped vẫn là real-model smoke test opt-in có chủ ý.
- Dependency audit: **No known vulnerabilities found**. Package local editable
  bị bỏ qua vì chưa phát hành trên PyPI.

## Giới hạn phạm vi

- Prediction CSV chủ ý không bị giới hạn bởi taxonomy annotation-only này;
  model configuration đã quyết định lớp prediction được tạo.
- Source media, pilot annotation data và prediction evidence hiện có không bị
  viết lại trong hardening change này.
