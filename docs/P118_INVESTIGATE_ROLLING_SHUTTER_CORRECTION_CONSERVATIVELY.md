# P118 — Investigate rolling-shutter correction conservatively

Active phase: **P118**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Rolling-shutter research report and bounded experimental mode". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Rolling-shutter research report and bounded experimental mode

- Goal: Explore geometric correction only with enough timing and motion evidence.
- Method: Use measured or documented readout timing, synchronized motion data where available, and controlled scenes. Separate optical-flow approximation from sensor-timing-based correction. Preserve the original and restrict correction when foreground motion violates a global model.
- Fixture: A fast pan across vertical lines with an independently moving foreground person.
- Oracle: The system reports residual error and does not warp the person using an unjustified global camera-motion assumption.
- Mutant that must fail: Apply one global shear correction to every object without validating motion.

Machine-readable fixture: [P118_INVESTIGATE_ROLLING_SHUTTER_CORRECTION_CONSERVATIVELY.json](P118_INVESTIGATE_ROLLING_SHUTTER_CORRECTION_CONSERVATIVELY.json).

Row time offset is `row_index * readout_seconds_per_row`. Correction is permitted
only when that readout is finite and greater than 0 and its source is `measured`.
A corrected row is `y' = y + velocity_y * row_time`. The report states the maximum
absolute row shift in pixels.

With readout `0.5` s/row the fixture rows are `(index 0, y 10, velocity 4)`,
`(index 2, y 20, velocity 4)`, and a foreground person `(index 1, y 8, velocity -2)`.
Row times are `0`, `1`, and `0.5`. Corrected coordinates are `10`, `24`, and `7`.
The max row shift is `4` pixels. The global-camera residual on the person is `3`
pixels. That residual is not a restored global shutter.

If readout is unknown or missing, a global warp labelled `rolling_shutter_correction`
is rejected. The honest output, with no such warp, is `recorded` and
`correction_applied false`. Rows are not shifted. Optical flow is not treated as
sensor-timing correction. One global camera shear is not applied to the person.
Claiming the correction restores a global shutter is rejected. Original `y` stays
in `preservedResults`.

`scripts/gates/p118_investigate_rolling_shutter_correction_conservatively.py` rejects
`applyMutant`, an unmeasured labelled warp, and a global-shutter restoration claim.
The evidence id stays in `preservedResults`. The decision is never `qualified` or
`allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p118*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P118-01 through TC-P118-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
