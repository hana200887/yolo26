# Provisional event annotations

This directory contains small, reviewable event annotations. It deliberately
does **not** contain the source video: raw media remains local under
`data/videos/` and is ignored by Git.

## Schema v1

Ground-truth input for `traffic-analytics evaluate` is a UTF-8 CSV with these
four required columns:

```csv
event_id,frame_index,class_name,direction
```

- `event_id`: positive, reviewer-assigned unique ID for the annotated event. It
  is not a ByteTrack ID.
- `frame_index`: zero-based frame at which the bottom-centre anchor first has
  crossed the configured line.
- `class_name`: one of the configured vehicle classes: `bicycle`, `car`,
  `motorcycle`, `bus`, or `truck`.
- `direction`: `IN` for negative-to-positive line-side movement and `OUT` for
  positive-to-negative movement. With the default horizontal line, `IN` means
  top-to-bottom image movement and `OUT` bottom-to-top image movement.

## Labeling protocol

1. Use the exact source checksum recorded in the paired provenance manifest.
2. Review consecutive frames, not a sparse contact sheet. The output overlay is
   allowed only to locate candidates; decide the event from the visible object
   and configured line, never from a tracker ID.
3. Create one event only when the same visible vehicle clearly changes side of
   the line. Use the first frame after the crossing as `frame_index`.
4. Exclude objects already on the post-crossing side at the start of the chosen
   window, occluded objects whose transition cannot be seen, and apparent
   crossings caused only by bounding-box or track-ID jitter.
5. Record the continuous frame window and reviewer method alongside each CSV.
   A single AI-assisted review is provisional; human verification or independent
   double annotation is required before publishing aggregate accuracy claims.

## Current pilot

`street_traffic-window-330-465.v1.events.csv` covers frames 330–465 only. It
is intentionally a narrowly scoped quality probe, not a full-video benchmark.
Its provenance, fixed review output, predictions, and limitations are recorded
in `docs/evidence/phase-2/`.
