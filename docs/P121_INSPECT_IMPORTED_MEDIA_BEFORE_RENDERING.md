# P121 — Inspect imported media before rendering

Active phase: **P121**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Media inspection report and import normalization policy". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Media inspection report and import normalization policy

- Goal: Determine source timing, geometry, color tags, rotation, and decoder support before assigning a look.
- Method: Parse metadata defensively, decode representative samples, and preserve the original URI or imported copy identity. Unknown transfer or range requires an explicit interpretation rather than silent guessing. Variable-frame-rate and rotated media remain supported only through declared policies.
- Fixture: An untagged HDR-looking clip, a rotated portrait clip, and a variable-frame-rate recording.
- Oracle: The importer separates known facts from user interpretation and does not flatten every source into one assumed SDR path.
- Mutant that must fail: Infer source color space solely from the filename extension.

Machine-readable fixture: [P121_INSPECT_IMPORTED_MEDIA_BEFORE_RENDERING.json](P121_INSPECT_IMPORTED_MEDIA_BEFORE_RENDERING.json).

The portrait fixture is a 2.0s, 24 fps, 48-frame `file://import/portrait.mov` clip.
`color_transfer` stays `bt709`. It is not rewritten to `logc3` or `arri_log`.
Video timebase is `1/24000` and audio timebase is `1/48000`. The content hash is
the sha256 of the evidence id bytes. Rotation is 90 degrees under
`declared-portrait-rotation`. Audio and video durations match, so there is no
A/V warning. `render_allowed` is true only because every required field is present.

Import inspection requires `duration_seconds`, `fps`, `video_timebase`,
`audio_timebase` (or `audio_absent` true), `color_transfer`, `color_primaries`,
`range`, `frame_count`, and `content_sha256`. When audio is present,
`audio_duration_seconds` is required as well. Unknown `rotation_degrees` is
also incomplete. Missing timestamps or a missing hash block rendering
(`render_allowed` false). The same block applies to any other missing required
field. If the caller sets `render_allowed` true anyway, the decision is
`rejected`. Honest incomplete media is `recorded` only when `render_allowed`
is false and `listed_missing_fields` matches the missing names exactly. Absent
fields stay null. They are not guessed, and cloud metadata is not fetched.

An audio/video duration delta above 0.04s, with audio present, stays in
`reasons` as `av-duration-delta-above-0.04s`. A delta of 0.04s does not warn.
`hide_av_delta` true on a warning rejects the document, and the warning is
still retained. `bt709` rewritten to `logc3` or `arri_log` is rejected and the
detected transfer is left unchanged.

Fields whose absence blocks rendering:

- `duration_seconds`, `video_timebase` (timestamps)
- `audio_timebase`, `audio_duration_seconds` when audio is present (timestamps)
- `content_sha256` (hash)
- `fps`, `color_transfer`, `color_primaries`, `range`, `frame_count`, `rotation_degrees`

`scripts/gates/p121_inspect_imported_media_before_rendering.py` rejects the
filename-extension mutant, a bt709 relabel, a hidden A/V delta, invented cloud
metadata, and a render flag on incomplete media. The evidence id stays in
`preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p121*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P121-01 through TC-P121-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
