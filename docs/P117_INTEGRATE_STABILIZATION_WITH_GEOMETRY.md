# P117 — Integrate stabilization with geometry

Active phase: **P117**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Stabilization geometry contract and alignment tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Stabilization geometry contract and alignment tests

- Goal: Keep camera-motion correction, crop, depth, and lens mapping in a shared coordinate system.
- Method: Represent stabilization as explicit per-frame transforms and valid regions. Apply corresponding mappings to depth and masks. Distinguish physical OIS, camera EIS, and post stabilization where known; avoid stacking unknown corrections without evidence.
- Fixture: A stabilized crop that moves across the original image while a depth map remains in source coordinates.
- Oracle: All render inputs align after transformation and the field-of-view report reflects the changing crop.
- Mutant that must fail: Stabilize RGB while leaving depth and subject masks untransformed.

Machine-readable fixture: [P117_INTEGRATE_STABILIZATION_WITH_GEOMETRY.json](P117_INTEGRATE_STABILIZATION_WITH_GEOMETRY.json).

A 4×2 source is translated by `(dx, dy) = (1, 0)`. Output `(x, y)` reads source
`(x - dx, y - dy)`. The sample at output `(1, 0)` reads source `(0, 0)` and
keeps depth `0`. The sample at output `(0, 0)` reads source `(-1, 0)`, which
is unknown and is not filled. The declared crop is `[0, 0, 3, 2]`, fully
inside the source and inside the valid region that stays on the canvas. Crop
coverage is `6/8 = 0.75`. The source horizontal field of view, `90°`, becomes
about `71.5650511771°`. Coverage of `1` is valid only when the warp is zero.
`fill="generated"` or `inpaint` is rejected. A crop that changes `lens_id` or
image aspect without `cropRecorded` is rejected. Stabilization keeps the
source timestamp and `lens_id`.

`scripts/gates/p117_integrate_stabilization_with_geometry.py` rejects `applyMutant`,
a full-frame claim that hides lost borders, generated fill, and a depth or mask
translation that does not match RGB. The evidence id stays in `preservedResults`.
The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p117*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P117-01 through TC-P117-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
