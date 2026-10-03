# P092 — Separate metric and relative focus controls

Active phase: **P092**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Depth-unit contract and honest focus UI". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Depth-unit contract and honest focus UI

- Goal: Avoid displaying absolute distances unsupported by the depth estimator.
- Method: Type depth outputs as metric, inverse metric, relative depth, or relative inverse depth. Require a validated scale calibration before metric optics. Offer relative focus and artist-controlled blur for uncalibrated scenes, with clear labels and bounded defaults.
- Fixture: A monocular model output whose numeric scale changes after a scene cut.
- Oracle: The app does not interpret the raw value as metres and resets or realigns relative focus appropriately.
- Mutant that must fail: Label every model depth value as a physical distance.

Machine-readable fixture: [P092_SEPARATE_METRIC_AND_RELATIVE_FOCUS_CONTROLS.json](P092_SEPARATE_METRIC_AND_RELATIVE_FOCUS_CONTROLS.json).

`scripts/gates/p092_separate_metric_and_relative_focus_controls.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p092*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P092-01 through TC-P092-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
