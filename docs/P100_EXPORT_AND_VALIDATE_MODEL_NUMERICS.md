# P100 — Export and validate model numerics

Active phase: **P100**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Model conversion report and numerical regression suite". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Model conversion report and numerical regression suite

- Goal: Treat model conversion as a potential behavioral change, not merely a packaging step.
- Method: Compare original and exported outputs on a fixed representative corpus. Record operator substitutions, precision changes, unsupported operations, and backend versions. Quantization requires its own calibration and held-out assessment, especially near difficult boundaries.
- Fixture: Original and quantized model outputs on glass, hair, low light, and thin foreground objects.
- Oracle: The converted model meets declared depth and boundary tolerances or remains an experimental option.
- Mutant that must fail: Accept conversion because the exported file loads successfully.

Machine-readable fixture: [P100_EXPORT_AND_VALIDATE_MODEL_NUMERICS.json](P100_EXPORT_AND_VALIDATE_MODEL_NUMERICS.json).

`scripts/gates/p100_export_and_validate_model_numerics.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p100*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P100-01 through TC-P100-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
