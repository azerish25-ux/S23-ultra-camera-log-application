# P082 — Model exposure-dependent grain statistics

Active phase: **P082**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Grain-statistics model and exposure-series tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Grain-statistics model and exposure-series tests

- Goal: Control grain intensity and channel relationships in the appropriate material domain.
- Method: Begin with synthetic statistical fixtures, then fit licensed reference material. Measure variance, distribution, spatial spectrum, and channel covariance across exposure levels. Keep a simple Gaussian reference clearly labelled as scaffolding rather than physically complete film grain.
- Fixture: Uniform exposure patches spanning deep shadow through highlights and a neutral color patch.
- Oracle: The measured statistics match the profile targets without unwanted hue shifts or repeating overlays.
- Mutant that must fail: Add identical-strength monochrome noise to every output pixel after display encoding.

Machine-readable fixture: [P082_MODEL_EXPOSURE_DEPENDENT_GRAIN_STATISTICS.json](P082_MODEL_EXPOSURE_DEPENDENT_GRAIN_STATISTICS.json).

`scripts/gates/p082_model_exposure_dependent_grain_statistics.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p082*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P082-01 through TC-P082-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
