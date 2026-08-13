# Third-party notices

This repository distributes its own code under the AGPL-3.0-or-later terms in [LICENSE](LICENSE). Third-party packages and media keep their own licenses. This notice is an attribution index, not a replacement for the original license texts.

## Runtime dependencies

- [Ultralytics](https://github.com/ultralytics/ultralytics) 8.4.118 - AGPL-3.0. The project calls its public YOLO and persistent tracker APIs through `src/traffic_analytics/ultralytics_adapter.py`.
- [OpenCV Python](https://github.com/opencv/opencv-python) 4.14.0.94 - Apache-2.0.
- [LAP](https://github.com/gatagat/lap) 0.5.13 - BSD-2-Clause.
- [PyYAML](https://pyyaml.org/) 6.0.3 - MIT.
- [NumPy](https://numpy.org/) and [Pydantic](https://github.com/pydantic/pydantic) are declared direct runtime dependencies; consult their installed distributions for their full notices and terms.

## ByteTrack

ByteTrack is used through Ultralytics' configured public tracking integration (`configs/bytetrack.yaml`). This repository does not vendor the upstream ByteTrack implementation. See the [ByteTrack project](https://github.com/ifzhang/ByteTrack) and the Ultralytics distribution for their applicable notices.

## Demo source media

`examples/result.gif` is a derivative of **Street traffic.webm**, authored by **Editor** and available from [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Street_traffic.webm) under [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/). The original media is not included. Exact source and derivative checksums, the frame range, and evaluation limits are in [examples/README.md](examples/README.md) and [Phase 2 evidence](docs/evidence/phase-2/phase-2-evidence.md).
