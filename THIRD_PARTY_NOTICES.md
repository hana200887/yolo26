# Thông báo bên thứ ba

Repository này phát hành mã do mình viết theo [AGPL-3.0-or-later](LICENSE).
Package và media bên thứ ba giữ license riêng. Tài liệu này là chỉ mục
attribution, không thay thế văn bản license gốc.

## Dependency lúc chạy

- [Ultralytics](https://github.com/ultralytics/ultralytics) 8.4.118 —
  AGPL-3.0. Dự án gọi public YOLO và persistent tracker API qua
  `src/traffic_analytics/ultralytics_adapter.py`.
- [OpenCV Python](https://github.com/opencv/opencv-python) 4.14.0.94 —
  Apache-2.0.
- [LAP](https://github.com/gatagat/lap) 0.5.13 — BSD-2-Clause.
- [PyYAML](https://pyyaml.org/) 6.0.3 — MIT.
- [NumPy](https://numpy.org/) và [Pydantic](https://github.com/pydantic/pydantic)
  là dependency runtime trực tiếp; xem distribution đã cài để biết đầy đủ
  notices và điều khoản.

## ByteTrack

ByteTrack được dùng qua public tracking integration đã cấu hình của
Ultralytics (`configs/bytetrack.yaml`). Repository này không vendor upstream
ByteTrack. Xem [dự án ByteTrack](https://github.com/ifzhang/ByteTrack) và bản
phân phối Ultralytics để biết notices tương ứng.

## Media nguồn của demo

`examples/result.gif` là derivative của **Street traffic.webm**, tác giả là
**Editor**, có trên [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Street_traffic.webm)
theo [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/). Media gốc
không được đưa vào repository. Checksum source/derivative, khoảng frame và giới
hạn đánh giá nằm trong [nguồn gốc demo](examples/README.md) và
[bằng chứng Phase 2](docs/evidence/phase-2/phase-2-evidence.md).
