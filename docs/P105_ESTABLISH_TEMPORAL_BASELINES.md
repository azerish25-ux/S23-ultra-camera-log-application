# P105 — Establish temporal baselines

Active phase: **P105**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host reference for "Temporal baseline suite and artifact taxonomy". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Temporal baseline suite and artifact taxonomy

- Goal: Measure frame-independent depth and a simple stabilized baseline before adding a complex temporal model.
- Method: Render the same sequences with no stabilization, a documented confidence-aware baseline, and candidate temporal methods. Quantify scale drift, focus pumping, edge flicker, and lag separately. Preserve per-frame depth outputs for diagnosis.
- Fixture: A stationary scene followed by a moving subject and a sudden camera cut.
- Oracle: The benchmark exposes both flicker reduction and temporal lag instead of rewarding smoothness alone.
- Mutant that must fail: Average depth heavily and ignore the resulting delay behind moving subjects.

Machine-readable fixture: [P105_ESTABLISH_TEMPORAL_BASELINES.json](P105_ESTABLISH_TEMPORAL_BASELINES.json).

`scripts/gates/p105_establish_temporal_baselines.py` reads frame timestamps in
milliseconds and optional luma means. It records the mean interval, the maximum
gap relative to the nominal frame period, and flicker as the sample standard
deviation of the first differences of luma. A gap longer than 1.5 frame periods
is kept as `cadence_break` and is not smoothed into the mean. Hiding that gap
is rejected. A single still frame cannot establish a temporal baseline. One
pretty keyframe score is not the sequence baseline. The baseline is `recorded`
only when at least eight frames exist and the metrics are finite. It is never
`qualified` or `allowed`, and it is never physical temporal performance.

The fixture uses a 40 ms nominal period and timestamps 0, 40, 80, 120, 160,
200, 240, and 400. The last step is 160 ms, four nominal periods, so it is one
`cadence_break`. The mean interval stays 400/7 ms. The evidence id stays in
`preservedResults`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p105*.py' -v
```

## Non-claims

- This is an authored host reference, not a device probe and not a physical S23 measurement.
- It does not certify sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- A recorded host baseline is not physical temporal performance.
- TC-P105-01 through TC-P105-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
