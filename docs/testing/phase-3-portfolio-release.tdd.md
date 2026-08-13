# Phát hành portfolio Phase 3 — bằng chứng TDD

## Phạm vi và user journey

Phase này được rút ra từ kế hoạch Phase 3 đã duyệt sau khi PR #1 merge vào
`main`. Phạm vi chủ ý nhỏ và tái tạo được cho GitHub portfolio: không thêm
model, tracker, API, UI, webcam hay deployment feature.

| User journey | Cam kết có thể kiểm tra |
| --- | --- |
| Là recruiter, tôi có thể hiểu dự án và thấy kết quả thật trong vài phút. | README có section cần thiết, đủ bốn CLI command, link evidence thật và GIF gọn. |
| Là reviewer, tôi có thể xác định source demo và limitation. | GIF có check size/signature; attribution, checksum, frame range và caveat đánh giá có hỗ trợ AI được commit. |
| Là contributor, tôi có thể chạy lại project checks mà không tải model weights. | CI tồn tại, pin external action, dùng lockfile, loại opt-in model test, chạy lint, type, coverage và dependency audit. |

## Ghi nhận RED đến GREEN

| Giai đoạn | Lệnh | Kết quả quan sát | Điều được chứng minh |
| --- | --- | --- | --- |
| RED | `uv run --frozen pytest tests/repository/test_portfolio_contract.py -q` | `17 failed in 0.40s` | README bảy dòng cũ và thiếu demo, provenance, license, workflow không thỏa public portfolio contract. |
| RED checkpoint | `git commit` | `8142a37 test: define portfolio release contract` | Failing contract được giữ trên `feat/03-portfolio-release` trước implementation. |
| GREEN | `uv run --frozen pytest tests/repository/test_portfolio_contract.py -q` | `18 passed in 0.04s` | README, demo, provenance, license, notices và CI hoàn chỉnh thỏa repository-level contract. |

## Quality gate

Toàn bộ lệnh được chạy local trên Windows với Python 3.11.15 và `uv.lock` đã
commit.

| Gate | Lệnh | Kết quả |
| --- | --- | --- |
| Format | `uv run --frozen ruff format --check .` | PASS — 31 files already formatted |
| Lint | `uv run --frozen ruff check .` | PASS |
| Types | `uv run --frozen mypy src` | PASS — no issues in 11 source files |
| Tests và coverage | `uv run --frozen pytest -m "not model" --cov=traffic_analytics --cov-report=term-missing -q` | PASS — 107 passed, 1 model test deselected, 85.54% branch coverage |
| Dependency audit | `uv run --frozen pip-audit` | PASS — no known vulnerabilities; `traffic-analytics` local bị skip vì chưa phát hành PyPI |
| Link tài liệu và CI parse | kiểm tra local link và YAML | PASS — 12 local link resolve; `quality` job tồn tại |
| Secret-pattern scan | `rg` trên public text/workflow thay đổi | PASS — không có potential secret pattern |

## Kiểm tra demo

- `examples/result.gif` dùng frame 330–465 (bao gồm hai đầu) của locally
  reviewed derivative 30 FPS, lấy mỗi frame thứ ba.
- Output: 46 frame, 4.6 giây, 640 × 360, 5,168,836 byte (thấp hơn contract
  5 MiB: 5,242,880 byte).
- SHA-256: `e9506431491e241ce518f65450062d791da130eafeff70b3fd0af8d3a2f2d336`.
- Visual review được làm trên frame đầu, giữa và cuối GIF. Khung bao, track ID,
  quỹ đạo, vạch đếm, tổng hướng và FPS vẫn nhìn thấy sau downsampling.
- Attribution source và điều khoản derivative CC BY 3.0 ở
  [examples/README.md](../../examples/README.md). GIF chỉ là visual demo; cửa
  sổ một sự kiện đi kèm vẫn có hỗ trợ AI và không phải accuracy tổng quát.

## Review và khoảng trống đã biết

Code/security review của diff Phase 3 đã phát hiện và sửa một presentation issue
không chặn: mojibake dash trong `THIRD_PARTY_NOTICES.md` được thay bằng ASCII.
Workflow cuối có `contents` permission read-only, dùng `pull_request` thay vì
`pull_request_target`, không chứa secret và pin ba external action bằng SHA 40
ký tự.

GitHub Actions chưa chạy tại thời điểm record này vì branch chưa được push.
Trạng thái CI remote phải được kiểm tra sau một lần push trước khi merge PR
Phase 3.
