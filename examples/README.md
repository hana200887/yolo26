# Nguồn gốc của demo

`result.gif` là preview trực quan gọn nhẹ, không phải dataset đánh giá và cũng
không thay thế video nguồn.

## Thông tin derivative

| Hạng mục | Giá trị |
| --- | --- |
| Media nguồn | [Street traffic.webm](https://commons.wikimedia.org/wiki/File:Street_traffic.webm) |
| Tác giả nguồn | Editor (`https://www.youtube.com/user/Editor`) |
| License nguồn | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) |
| SHA-256 nguồn | `e5facb24baf755f0c1193999d823e99f6032661ad2bdef5cc28cc1cbbfde03e2` |
| Input derivative | `street_traffic-analyze.review-30fps.mp4` local; không commit |
| Khoảng frame | Frame 330–465 (bao gồm hai đầu) của lượt chạy đã chú thích 30 FPS |
| Lấy mẫu và kích thước | Mỗi frame thứ ba, 46 frame tại 10 FPS, 640 × 360 pixel |
| Mã hóa GIF | 64 màu, không dithering, 4.6 giây, 5,168,836 byte |
| SHA-256 GIF | `e9506431491e241ce518f65450062d791da130eafeff70b3fd0af8d3a2f2d336` |

Overlay output được thêm bởi dự án này. Video gốc, MP4 đã chú thích, video thô
và model weights không commit để repository gọn nhẹ và để người dùng lấy source
qua trang license của nó.

## Giới hạn đánh giá

Cùng cửa sổ này có một nhãn `bus, IN` được tạo qua visual review có hỗ trợ AI.
Nhãn chưa được một người đánh giá độc lập xác minh. Vì vậy GIF chỉ minh họa
artifact trực quan của pipeline; nó không chứng minh độ chính xác detection,
tracking hay counting.

Lệnh đầy đủ, runtime environment, source metadata và giới hạn đánh giá được
ghi trong [bằng chứng Phase 2](../docs/evidence/phase-2/phase-2-evidence.md).
