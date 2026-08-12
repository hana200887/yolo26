# Phase 2 evidence: licensed real-traffic pilot

## What this proves

This phase proves that the repository can run YOLO26 + ByteTrack on a real,
licensed local traffic clip, emit reviewable artifacts, and evaluate event
counts against a tracker-independent annotation schema. It does **not** claim
general accuracy, real-time GPU performance, or a human-verified benchmark.

## Source and attribution

- Title: **Street traffic.webm** — street traffic in San Francisco.
- Author: **Editor** (`https://www.youtube.com/user/Editor`).
- Source page: `https://commons.wikimedia.org/wiki/File:Street_traffic.webm`.
- License: [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/).
- Change made: this project runs object detection/tracking and creates an
  annotated derivative for local review; the original video is not committed.

The exact source file and license metadata are recorded in
[`street_traffic.provenance.json`](street_traffic.provenance.json). Its SHA-256
is `e5facb24baf755f0c1193999d823e99f6032661ad2bdef5cc28cc1cbbfde03e2`.

## Reproducible run

Run from the repository root after obtaining the source file whose checksum
matches the provenance manifest:

```powershell
uv run --frozen traffic-analytics analyze `
  --source data/videos/street_traffic.webm `
  --config configs/default.yaml `
  --no-preview `
  --max-frames 1050
```

Observed runtime on 2026-08-12:

| Item | Observed value |
| --- | --- |
| Input | VP8/WebM, 1,920 × 1,080, 1,050 decoded frames, 35.004 s |
| Model | `yolo26n.pt`, SHA-256 `9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef` |
| Config | `configs/default.yaml`, SHA-256 `211e99be881db92d7a0e8dbe5763514412172ac6ffdbd3d64a95216e02f9b3cb` |
| Runtime | Python 3.11.15, Ultralytics 8.4.118, OpenCV 4.14.0, Torch 2.13.0+cpu |
| Accelerator | CPU only (`torch.cuda.is_available() == false`) |
| Full run elapsed time | 79.7015 s |
| Processing throughput | 13.17 FPS |
| Tracked observations | 10,918 |
| Predicted crossing events | 7 |

The initial output video received a malformed 1,000 FPS timestamp from OpenCV
for this WebM. `street_traffic-analyze.review-30fps.mp4` is a local H.264
re-encode of the same annotated frame sequence at 30 FPS and 35.000 s, created
only for visual review. The codebase now rejects implausible source FPS values
(>240) and falls back to 30 FPS. This remediation is verified by a regression
test.

Local artifacts (all ignored by Git) from this run:

```text
data/outputs/street_traffic-analyze.events.csv
data/outputs/street_traffic-analyze.summary.json
data/outputs/street_traffic-analyze.mp4
data/outputs/street_traffic-analyze.review-30fps.mp4
```

## Provisional event evaluation slice

The event labels at
[`data/annotations/street_traffic-window-330-465.v1.events.csv`](../../../data/annotations/street_traffic-window-330-465.v1.events.csv)
cover one continuous 136-frame window (frames 330–465; 4.53 s at 30 FPS).
The reviewer visually confirmed one `bus,IN` crossing at frame 357. The labels
were produced by **AI-assisted visual review and have not received independent
human verification**.

Predictions within the same window are frozen in
[`street_traffic-window-330-465.predictions.csv`](street_traffic-window-330-465.predictions.csv),
so this exact small evaluation can be rerun without checking in the video:

```powershell
uv run --frozen traffic-analytics evaluate `
  --predictions docs/evidence/phase-2/street_traffic-window-330-465.predictions.csv `
  --ground-truth data/annotations/street_traffic-window-330-465.v1.events.csv `
  --frame-tolerance 5
```

Expected result:

```json
{
  "total_predictions": 5,
  "total_ground_truth": 1,
  "true_positives": 1,
  "false_positives": 4,
  "false_negatives": 0,
  "precision": 0.2,
  "recall": 1.0,
  "f1": 0.33333333333333337,
  "absolute_count_error": 4,
  "frame_tolerance": 5
}
```

This deliberately exposes a weakness: temporary tracker/detection variation in
crowded, partially occluded traffic generated four unmatched events in the
review window. It is a useful baseline artifact, not a performance claim.

## Review limits and next data step

- This is one historical street scene, not a representative data set.
- The fixed line is scene-specific; calibration must be repeated for another
  camera.
- The pilot annotation is narrow and AI-assisted. Before reporting aggregate
  accuracy, label full continuous clips, use two independent human annotators,
  resolve disagreements, and record agreement.
- Source media, model weights, and output videos stay local to keep the GitHub
  repository small. Anyone reproducing the work must obtain the source via its
  license page and verify its checksum.
