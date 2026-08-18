# LOOP-0019A-QW04-R3 — operator handoff

Physical run: 2026-08-18
Launcher: `TukeVision.bat`
Runtime state: `STOPPED`
Source state: `CLOSED`

## Selected real case

- Signal: `BS-5648A0B64CED8334`
- Camera: `CAM-004`
- Track: `TRK-CAM-004-000048`
- Rule: `repeated_activity`
- Rule score: `20.0`
- Static JPEG: `CAM-004/EVD-C0016D34938247CCBEFCB730DC9233C5/frame.jpg`
- Temporal clip: `clips/CAM-004/CLP-882DC0CD0FEE4411B473F277431FA0DA.mp4`
- Clip SHA-256: `f8d0a9ada335a5cc0619b49d7941ff26d9b1e7ff97fb72531a98ec085d0fa8a4`
- Declared temporal span: `6.703 s`
- Decoded media: `19 frames`, `640x360`, `mpeg4`, container duration `3.8 s`
- QW-00 classification: `NOT_REVIEWED`

The QW-00 resolver confirms that both the selected JPEG and MP4 exist beneath
`data/runtime_evidence`. The MP4 decodes successfully and its computed SHA-256
matches both the clip sidecar and QW-00 record.

## Operator actions

Run `review_behavior_signals.bat`. The bounded dataset contains four records.
Press `S` on the first two records, which reference media already evicted by the
bounded retention policy. On the `CAM-004` case above:

1. Press `J` to open the JPEG.
2. Press `C` to open and play the MP4.
3. Compare camera, track and observed activity.
4. Choose classification `1`–`5` and answer both sufficiency prompts.
5. Press `Q` when finished to persist the human review.

No human sufficiency or classification result is claimed by this handoff.
