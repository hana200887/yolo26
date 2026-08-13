# Annotation sự kiện tạm thời

Thư mục này chứa annotation sự kiện nhỏ, có thể review. Nó chủ ý **không**
chứa video nguồn: media thô giữ local dưới `data/videos/` và bị Git ignore.

## Schema v1

Ground-truth input cho `traffic-analytics evaluate` là UTF-8 CSV có đúng bốn
cột bắt buộc:

```csv
event_id,frame_index,class_name,direction
```

- `event_id`: ID dương, duy nhất do reviewer gán cho sự kiện annotation. Đây
  không phải ByteTrack ID.
- `frame_index`: frame zero-based mà bottom-centre anchor lần đầu đã đi qua
  vạch được cấu hình.
- `class_name`: một trong canonical vehicle class: `bicycle`, `car`,
  `motorcycle`, `bus`, `truck`.
- `direction`: `IN` cho chuyển động từ phía âm sang phía dương của vạch và
  `OUT` cho phía dương sang phía âm. Với horizontal line mặc định, `IN` là
  chuyển động ảnh từ trên xuống dưới và `OUT` là từ dưới lên trên.

## Protocol gán nhãn

1. Dùng đúng source checksum ghi trong paired provenance manifest.
2. Review frame liên tiếp, không dùng sparse contact sheet. Output overlay chỉ
   được phép giúp tìm candidate; quyết định sự kiện dựa trên object nhìn thấy
   và configured line, không bao giờ dựa vào tracker ID.
3. Chỉ tạo một event khi cùng visible vehicle đổi phía của line rõ ràng. Dùng
   frame đầu tiên sau giao cắt làm `frame_index`.
4. Loại object đã ở phía sau giao cắt tại đầu cửa sổ, object bị che mà không
   thấy được chuyển tiếp, và apparent crossing chỉ do bounding-box hoặc
   track-ID jitter.
5. Ghi continuous frame window và reviewer method cạnh mỗi CSV. Một lần review
   có hỗ trợ AI chỉ là tạm thời; cần human verification hoặc double annotation
   độc lập trước khi công bố aggregate accuracy.

## Pilot hiện tại

`street_traffic-window-330-465.v1.events.csv` chỉ bao phủ frame 330–465. Nó
cố ý là quality probe hẹp, không phải full-video benchmark. Provenance, fixed
review output, prediction và giới hạn nằm trong `docs/evidence/phase-2/`.
