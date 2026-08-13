# Tài liệu trực quan Phase 4 — bằng chứng TDD

## Phạm vi và user journey

Phase này được triển khai trực tiếp trên `main` theo yêu cầu. Phạm vi dừng ở
tài liệu và presentation cho GitHub: không đổi model, tracker, metric, API hay
runtime pipeline.

| User journey | Cam kết có thể kiểm tra |
| --- | --- |
| Là người xem GitHub, tôi có thể hiểu đường đi từ video đến artifact đếm. | README hiển thị sơ đồ kiến trúc SVG và trỏ đến Mermaid source chỉnh sửa được. |
| Là reviewer, tôi có thể lần từ media nguồn đến metric pilot và giới hạn của nó. | Evidence Phase 2 hiển thị sơ đồ provenance/evaluation; sơ đồ nêu rõ CC BY 3.0, nhãn có hỗ trợ AI, ground truth và cảnh báo không phải benchmark tổng quát. |
| Là contributor, tôi có thể kiểm tra sơ đồ mà không phụ thuộc một editor riêng. | Mỗi sơ đồ có `.svg` portable và `.mmd` editable; contract kiểm tra chữ thiết yếu, XML hợp lệ và toạ độ gốc của text nằm trong `viewBox`. |
| Là người đọc tiếng Việt, tôi có thể dùng toàn bộ tài liệu public trong cùng ngôn ngữ. | README, demo provenance, evidence, notices, README sơ đồ và các record TDD được Việt hóa; văn bản AGPL giữ nguyên bản legal chuẩn. |

## Ghi nhận RED → GREEN

| Giai đoạn | Lệnh | Kết quả quan sát | Điều được chứng minh |
| --- | --- | --- | --- |
| RED | `uv run --frozen pytest tests/repository/test_visual_documentation_contract.py -q` | `5 failed in 0.15s` | Chưa có hai SVG/Mermaid, README tiếng Việt hay liên kết provenance trực quan. |
| RED checkpoint | `git commit -m "test: define visual documentation contract"` | `e4b8d17` | Contract thất bại được giữ trên `main` trước implementation. |
| GREEN | `uv run --frozen pytest tests/repository/test_portfolio_contract.py tests/repository/test_visual_documentation_contract.py -q` | `23 passed in 0.06s` | Nội dung, liên kết và artifact mới thỏa portfolio contract. |
| Review RED | `uv run --frozen pytest tests/repository/test_visual_documentation_contract.py -q` | `4 failed, 6 passed in 0.09s` | Review độc lập phát hiện connector SVG rời, topology evaluation sai, nhãn precision/accuracy mơ hồ và annotation README chưa Việt hóa. |
| Review RED checkpoint | `git commit -m "test: cover visual diagram review findings"` | `ef132d9` | Các finding được đóng thành contract trên `main` trước khi sửa. |
| GREEN cuối | `uv run --frozen pytest tests/repository/test_portfolio_contract.py tests/repository/test_visual_documentation_contract.py -q` | `28 passed in 0.07s` | Nội dung, topology connector, XML/toạ độ, nhãn precision-recall, liên kết và bản dịch tài liệu thỏa contract. |

## Artifact được thêm

| Artifact | Vai trò |
| --- | --- |
| [`architecture.svg`](../diagrams/architecture.svg) + [`architecture.mmd`](../diagrams/architecture.mmd) | Mô tả video cục bộ → YOLO26 → ByteTrack → quỹ đạo → đếm qua vạch → MP4/CSV/JSON. |
| [`evaluation-provenance.svg`](../diagrams/evaluation-provenance.svg) + [`evaluation-provenance.mmd`](../diagrams/evaluation-provenance.mmd) | Liên kết source CC BY 3.0, manifest SHA-256, lượt chạy local, nhãn có hỗ trợ AI, đối sánh sự kiện và metric pilot. |
| [`README.md`](../../README.md) | Entry point portfolio tiếng Việt, nhúng cả hai SVG. |
| [`phase-2-evidence.md`](../evidence/phase-2/phase-2-evidence.md) | Đặt sơ đồ provenance ngay cạnh lời giải thích về phạm vi evidence. |

## Kiểm tra cuối

| Gate | Lệnh | Kết quả |
| --- | --- | --- |
| Format | `uv run --frozen ruff format --check .` | PASS — 34 files already formatted |
| Lint | `uv run --frozen ruff check .` | PASS |
| Types | `uv run --frozen mypy src` | PASS — no issues in 11 source files |
| Tests và coverage | `uv run --frozen pytest -m "not model" --cov=traffic_analytics --cov-report=term-missing -q` | PASS — 118 passed, 1 model test deselected, 85.54% coverage |
| Dependency audit | `uv run --frozen pip-audit` | PASS — no known vulnerabilities; package local chưa phát hành PyPI nên không audit được |
| Khoảng trắng diff | `git diff --check` | PASS — không có lỗi whitespace |

## Kiểm tra hiển thị và giới hạn còn lại

- Hai file SVG đã qua XML parse, `viewBox`, toạ độ text và endpoint connector
  bằng repository contract; ảnh không cần JavaScript hay asset remote để hiển
  thị. Review độc lập đã bắt hai luồng connector bị rời và chúng đã được sửa
  trước GREEN cuối.
- Re-review cuối đã đo trực tiếp copy trong SVG: các dòng metric rộng 217–265
  px trong vùng card 332 px; hai dòng caveat rộng 516 px và 691 px trong vùng
  866 px. Không còn overflow hay blocker hiển thị.
- Đã thử render preview local bằng trình xem trong app. Chính sách URL của app
  chặn `file:///` nên không thể thực hiện visual preview tại đó; không lách hạn
  chế này. GitHub sẽ render SVG trực tiếp sau khi commit/push, vì vậy trạng thái
  render trên remote chỉ được xác nhận sau push.
- Metric vẫn chỉ là pilot: cửa sổ 136 frame có hỗ trợ AI, không có review độc
  lập và không phải benchmark tổng quát. Sơ đồ làm rõ giới hạn này, không làm
  mạnh hơn claim hiện có.
