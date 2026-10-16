# P107 — Align relative depth scale and offset

Active phase: **P107**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Relative-depth alignment and focus-pumping tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Relative-depth alignment and focus-pumping tests

- Goal: Prevent arbitrary model normalization from becoming visible focus breathing.
- Method: Estimate robust alignment only over valid, stable correspondences and use the model appropriate to its output semantics. Bound fits, reject ill-conditioned scenes, and retain confidence. Do not perform global min-max normalization independently on every frame.
- Fixture: A scene where a close object enters the frame while the background remains stationary.
- Oracle: Background blur remains stable unless its actual geometry or selected focus changes.
- Mutant that must fail: Renormalize each depth map using its current minimum and maximum.

Machine-readable fixture: [P107_ALIGN_RELATIVE_DEPTH_SCALE_AND_OFFSET.json](P107_ALIGN_RELATIVE_DEPTH_SCALE_AND_OFFSET.json).

`scripts/gates/p107_align_relative_depth_scale_and_offset.py` fits relative depth with the
normal equations `depth_ref ≈ scale * depth_rel + offset` on at least three finite
pairs and returns scale, offset, and RMSE. Hold-out pairs are scored separately.
It rejects a negative scale, a metric-metre label on a relative reference, a forced
unit scale whose RMSE exceeds tolerance, hold-out leakage, and `applyMutant`.
The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p107*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P107-01 through TC-P107-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
