# P088 — Validate the combined material pipeline

Active phase: **P088**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Combined film-material regression suite". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Combined film-material regression suite

- Goal: Evaluate interactions that isolated effect tests cannot reveal.
- Method: Render controlled exposure sequences with denoise, virtual optics, negative response, grain, halation, bloom, and print finishing. Measure seams, clipping, noise amplification, temporal shimmer, and color drift. Use ablations to identify which stage causes a failure.
- Fixture: A moving bright subject crossing a dark textured background while grain and halation are enabled.
- Oracle: The complete sequence remains temporally stable and each effect can be disabled to isolate artifacts.
- Mutant that must fail: Approve the combined pipeline because every effect passed its own still-image test.

Machine-readable fixture: [P088_VALIDATE_THE_COMBINED_MATERIAL_PIPELINE.json](P088_VALIDATE_THE_COMBINED_MATERIAL_PIPELINE.json).

`scripts/gates/p088_validate_the_combined_material_pipeline.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p088*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P088-01 through TC-P088-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
