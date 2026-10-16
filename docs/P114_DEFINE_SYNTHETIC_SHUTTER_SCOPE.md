# P114 — Define synthetic shutter scope

Active phase: **P114**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Synthetic-shutter eligibility policy and limitation tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Synthetic-shutter eligibility policy and limitation tests

- Goal: Make deferred motion rendering an explicit optional operation with clear source requirements.
- Method: Estimate available temporal sampling and existing source blur before synthesizing additional exposure integration. State that already blurred or undersampled motion cannot always be corrected. Preserve original cadence and record any interpolation or frame synthesis.
- Fixture: A short-exposure source, a heavily blurred source, and a rapidly moving thin object captured with insufficient temporal samples.
- Oracle: The tool applies only its qualified operation and labels unsupported reconstruction rather than promising perfect shutter conversion.
- Mutant that must fail: Claim that any video can be converted exactly to any shutter angle.

Machine-readable fixture: [P114_DEFINE_SYNTHETIC_SHUTTER_SCOPE.json](P114_DEFINE_SYNTHETIC_SHUTTER_SCOPE.json).

`scripts/gates/p114_define_synthetic_shutter_scope.py` records a synthetic shutter scope only when its frame weights sum to 1 within 1e-6, it names the shutter angle and fps it simulates, and it does not label captured-only integration as a longer sensor exposure. Estimated frames must set `contains_estimated` true. If estimated frames exist and `disclosed` is false, the scope is rejected as a hidden hallucination. The evidence id stays in `preservedResults`. The decision is `recorded` or `rejected`, never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p114*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P114-01 through TC-P114-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
