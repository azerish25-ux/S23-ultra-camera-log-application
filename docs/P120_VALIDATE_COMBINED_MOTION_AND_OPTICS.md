# P120 — Validate combined motion and optics

Active phase: **P120**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Motion-optics integration benchmark and release envelope". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Motion-optics integration benchmark and release envelope

- Goal: Test temporal interactions between shutter simulation, stabilization, depth, and focus.
- Method: Use a fixed graph order with shared geometry and timing semantics. Compare ablations and perfect-motion fixtures. Record whether a defect originates from source blur, flow, stabilization, depth, or compositing before changing multiple algorithms.
- Fixture: A handheld focus pull with foreground occlusion, bright bokeh, and synthetic shutter enabled.
- Oracle: The complete clip maintains coherent motion without doubled edges, drifting masks, or discontinuous focus.
- Mutant that must fail: Approve each temporal effect independently and skip their combined regression.

Machine-readable fixture: [P120_VALIDATE_COMBINED_MOTION_AND_OPTICS.json](P120_VALIDATE_COMBINED_MOTION_AND_OPTICS.json).

The combined report must include `shutter_angle`, `fps`, `exposure_seconds`,
`interpolation_fraction`, `estimated_disclosed`, `stabilization_crop_fraction`,
`rolling_shutter_readout` (`measured` or `unknown`), and `correction_applied`.
`exposure_seconds` must equal `(shutter_angle/360)/fps` within `1e-9`.
`interpolation_fraction > 0` with `estimated_disclosed` false is rejected.
`correction_applied` true while readout is `unknown` is rejected. A missing
field is rejected. A spot-check that only includes `shutter_angle` and claims
the combination passed is rejected. An ablation that claims the combination
passed is rejected. The fixed graph order is
`source_blur>shutter>interpolation>stabilization>depth>focus>compositing`.
Consistent honest reports, including a perfect-motion fixture and a disclosed
ablation that does not claim the combination, are recorded.

`scripts/gates/p120_validate_combined_motion_and_optics.py` rejects `applyMutant`,
missing report fields, exposure mismatches, undisclosed interpolation, and
rolling-shutter correction without a measured readout. The evidence id stays in
`preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p120*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P120-01 through TC-P120-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
