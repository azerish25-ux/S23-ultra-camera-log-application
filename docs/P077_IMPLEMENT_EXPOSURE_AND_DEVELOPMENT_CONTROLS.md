# P077 — Implement exposure and development controls

Active phase: **P077**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Exposure-development-grade parameter contract". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Exposure-development-grade parameter contract

- Goal: Make exposure compensation, push/pull interpretation, and final contrast distinct operations.
- Method: Exposure changes scale incident scene exposure before the negative response. Development controls modify explicitly modelled material parameters and are labelled approximations unless measured. A final grade acts after the declared finishing stage. Save all three independently.
- Fixture: Three renders adjusted to similar midtone brightness by exposure, development, and display contrast respectively.
- Oracle: The graph records different operations and preserves their different shadow, highlight, and grain consequences.
- Mutant that must fail: Implement every control as the same post-LUT contrast multiplier.

Machine-readable fixture: [P077_IMPLEMENT_EXPOSURE_AND_DEVELOPMENT_CONTROLS.json](P077_IMPLEMENT_EXPOSURE_AND_DEVELOPMENT_CONTROLS.json).

`scripts/gates/p077_implement_exposure_and_development_controls.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p077*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P077-01 through TC-P077-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
