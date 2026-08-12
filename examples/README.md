# Demo media provenance

`result.gif` is a compact visual preview, not an evaluation data set or a replacement for the source video.

## Derivative details

| Item | Value |
| --- | --- |
| Source media | [Street traffic.webm](https://commons.wikimedia.org/wiki/File:Street_traffic.webm) |
| Source author | Editor (`https://www.youtube.com/user/Editor`) |
| Source license | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) |
| Source SHA-256 | `e5facb24baf755f0c1193999d823e99f6032661ad2bdef5cc28cc1cbbfde03e2` |
| Derivative input | Local `street_traffic-analyze.review-30fps.mp4`; not committed |
| Frame range | Inclusive frames 330-465 of the 30 FPS annotated run |
| Sampling and size | Every third frame, 46 frames at 10 FPS, 640 x 360 pixels |
| GIF encoding | 64 colors, no dithering, 4.6 seconds, 5,168,836 bytes |
| GIF SHA-256 | `e9506431491e241ce518f65450062d791da130eafeff70b3fd0af8d3a2f2d336` |

The pipeline output overlay was added by this project. The original source, annotated MP4, raw video, and model weights are not committed so the repository remains small and users can obtain the source through its license page.

## Evaluation limit

The same window has a single `bus, IN` label created by AI-assisted visual review. It has not received independent human verification. The GIF therefore demonstrates the pipeline's visual artifacts only; it does not establish detection, tracking, or counting accuracy.

The full command, runtime environment, source metadata, and evaluation caveats are recorded in [Phase 2 evidence](../docs/evidence/phase-2/phase-2-evidence.md).
