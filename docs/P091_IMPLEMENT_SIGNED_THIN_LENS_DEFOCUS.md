# P091 — Implement signed thin-lens defocus

Active phase: **P091**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Thin-lens reference code and dimensional tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Thin-lens reference code and dimensional tests

- Goal: Create an independently testable geometric reference for blur magnitude and foreground-background ordering.
- Method: Use consistent length units and explicit f-number. Compute signed circle-of-confusion diameter from focal length, object distance, focus distance, and aperture. Convert to output pixels through the virtual gate. Handle infinity and reject impossible geometry.
- Fixture: Objects in front of, on, and behind a focus plane, including an infinitely distant background.
- Oracle: Focus-plane blur is zero, signs distinguish near and far, and stopping down scales diameter as expected.
- Mutant that must fail: Use a T-stop directly as an f-number without accounting for transmission semantics.

Machine-readable fixture: [P091_IMPLEMENT_SIGNED_THIN_LENS_DEFOCUS.json](P091_IMPLEMENT_SIGNED_THIN_LENS_DEFOCUS.json).

`scripts/gates/p091_implement_signed_thin_lens_defocus.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p091*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P091-01 through TC-P091-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
