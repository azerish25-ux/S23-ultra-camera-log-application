# P093 — Implement aperture and bokeh shape models

Active phase: **P093**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Aperture kernel library and point-light tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Aperture kernel library and point-light tests

- Goal: Create controlled blur kernels with explicit shape and normalization.
- Method: Start with a circular reference, then add polygonal blades and optional measured or creative asymmetry. Define kernel support, energy normalization, sampling quality, and behavior near image boundaries. Keep a parameter reset that returns exactly to the reference.
- Fixture: A grid of bright points at different depths and positions across the frame.
- Oracle: Bokeh shape and energy follow the selected model without random brightness changes when aperture shape changes.
- Mutant that must fail: Use an unnormalized polygon mask whose brightness grows with blur radius.

Machine-readable fixture: [P093_IMPLEMENT_APERTURE_AND_BOKEH_SHAPE_MODELS.json](P093_IMPLEMENT_APERTURE_AND_BOKEH_SHAPE_MODELS.json).

`scripts/gates/p093_implement_aperture_and_bokeh_shape_models.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p093*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P093-01 through TC-P093-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
