# Sửa lỗi review Phase 1 — bằng chứng TDD

## Phạm vi và user journey

Báo cáo này bao phủ ba phát hiện có thể hành động từ defect-first review của
Phase 1. Không dùng file kế hoạch bên ngoài.

- Là một evaluator, tôi cần khớp sự kiện một-một hợp lệ nhiều nhất trong dung
  sai frame đã cấu hình, để precision, recall và F1 không phụ thuộc thứ tự input.
- Là một traffic analyst, tôi cần ID biến mất ngắn hạn vẫn giữ tuổi trong
  ByteTrack buffer, để vehicle quay lại không bị minimum-age guard loại bỏ.
- Là một người dùng video, tôi cần lượt chạy lỗi không để lại final output,
  để video dở dang không bị hiểu nhầm là phân tích hoàn tất.

## Ghi nhận RED → GREEN

| Hành vi | Bằng chứng RED | Bằng chứng GREEN | Cam kết |
| --- | --- | --- | --- |
| Khớp đánh giá maximum-cardinality | `uv run --frozen pytest tests/unit/test_evaluation.py tests/integration/test_ultralytics_adapter.py tests/e2e/test_local_video_flow.py -q` → 3 failed, gồm TP `1` thay vì `2` | Cùng lệnh sau khi sửa → 19 passed | Sự kiện được nhóm theo lớp/hướng, sắp xếp theo frame và khớp một-một để tối đa số cặp trong dung sai. |
| Tuổi track qua gap ngắn rồi hết hạn theo buffer | Cùng lệnh RED → ID quay lại có tuổi `1` thay vì `3` | Cùng lệnh sau khi sửa → 19 passed | Trạng thái tuổi/last-seen theo ID được giữ đến `track_buffer`, sau đó prune. |
| Lượt chạy lỗi không lộ file chưa hoàn thiện | Cùng lệnh RED → `.mp4` còn trong output directory | Cùng lệnh sau khi sửa → 19 passed | Video, event và summary dùng temporary path cùng directory; lỗi sẽ đóng writer và xóa artifact temporary/published của lượt chạy hiện tại. |
| Lỗi ghi event muộn không lộ video | Bổ sung regression test sau atomic-output refactor | `uv run --frozen pytest tests/e2e/test_local_video_flow.py tests/unit/test_evaluation.py tests/integration/test_ultralytics_adapter.py -q` → 20 passed | Artifact chỉ publish sau khi event CSV và summary cùng tạo thành công. |

## Xác minh cuối

```powershell
uv run --frozen ruff format --check .
uv run --frozen ruff check .
uv run --frozen mypy src
uv run --frozen pytest --cov=traffic_analytics --cov-report=term-missing -q
```

Kết quả: Ruff và strict mypy pass; **74 passed, 1 skipped**; branch-aware
coverage là **84.07%** (tối thiểu 80%).

## Khoảng trống đã biết

- Real model test vẫn opt-in (`RUN_MODEL_TESTS=1`) vì có thể load weights local
  và đã được smoke-test riêng trong workspace này.
- Phase 2 sẽ thêm traffic clip có license phù hợp, manual ground truth, visual
  review và bằng chứng performance đã đo.
- Git checkpoint commit không được tạo vì checkout lúc đó chưa cấu hình Git
  author identity; không tự tạo identity.
