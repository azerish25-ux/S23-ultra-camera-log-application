# P128 — Validate long-form development end to end

Active phase: **P128**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "End-to-end deferred-development acceptance report". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

End-to-end deferred-development acceptance report

- Goal: Prove that the deferred workflow survives realistic interruptions and large media.
- Method: Run complete import, recipe edit, render, cancel, resume, verify, publish, and re-open workflows. Use rotated, variable-rate, audio-bearing, high-resolution, and corrupt-edge fixtures. Record limitations separately for software and physical-device execution.
- Fixture: A multi-minute clip with audio, orientation metadata, temporal effects, and one process termination during rendering.
- Oracle: The final accepted result has correct timing, orientation, audio, provenance, and no duplicated checkpoint boundary frames.
- Mutant that must fail: Validate only short silent landscape clips.

Machine-readable fixture: [P128_VALIDATE_LONG_FORM_DEVELOPMENT_END_TO_END.json](P128_VALIDATE_LONG_FORM_DEVELOPMENT_END_TO_END.json).

`scripts/gates/p128_validate_long_form_development_end_to_end.py` records a complete honest frame account. Every index from 0 inclusive to `expected_frames` exclusive must appear exactly once in `accounted_frames`. A missing or duplicate index is rejected, and so is an index outside that span. `checkpoint_frames` must be strictly increasing and the last checkpoint must be `<= expected_frames-1`; a break is rejected. `abs(audio_duration-video_duration) > 0.04` is rejected unless `audio_absent` is true. `spot_check_only` true is rejected even when the lists look complete. The host fixture uses `expected_frames` 6 so the account stays fast; it stands in for the multi-minute rule and is not a physical capture. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`. A recorded account does not certify physical playback.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p128*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P128-01 through TC-P128-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
