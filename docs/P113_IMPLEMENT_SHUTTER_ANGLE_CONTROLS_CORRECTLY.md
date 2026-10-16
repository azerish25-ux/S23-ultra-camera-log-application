# P113 — Implement shutter-angle controls correctly

Active phase: **P113**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Shutter-angle model and exposure feasibility tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Shutter-angle model and exposure feasibility tests

- Goal: Translate creative shutter angle into a feasible physical exposure request.
- Method: Compute exposure from rational frame rate and angle, then validate sensor limits and actual applied results. Keep requested angle separate from effective exposure. When light levels prevent the desired setting, explain the tradeoff without silently changing cadence.
- Fixture: One-hundred-eighty-degree shutter at twenty-four frames per second and a requested exposure exceeding the selected sensor interval.
- Oracle: The first maps to approximately one forty-eighth second and the second is rejected or visibly constrained.
- Mutant that must fail: Treat shutter angle as an arbitrary blur-strength percentage.

Exposure time seconds = (shutter_angle_degrees / 360) / fps. Frame interval seconds = 1/fps.
180 deg at 24 fps = (180/360)/24 = 1/48 s. An angle above 360 is rejected. Exposure longer than the frame interval is rejected unless `synthetic_integration` is explicitly true. A reported 180-degree shutter whose exposure is not that duration is rejected. The host fixture leaves `sensor_confirmed` false, so it does not claim the sensor used the angle, and the decision is `recorded`.

Machine-readable fixture: [P113_IMPLEMENT_SHUTTER_ANGLE_CONTROLS_CORRECTLY.json](P113_IMPLEMENT_SHUTTER_ANGLE_CONTROLS_CORRECTLY.json).

`scripts/gates/p113_implement_shutter_angle_controls_correctly.py` rejects `applyMutant` and an exposure that does not match the requested angle. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p113*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P113-01 through TC-P113-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
