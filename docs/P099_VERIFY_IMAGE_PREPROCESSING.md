# P099 — Verify image preprocessing

Active phase: **P099**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Preprocessing reference and host-device tensor comparisons". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Preprocessing reference and host-device tensor comparisons

- Goal: Prevent silent accuracy loss from wrong normalization, resizing, channel order, or crop mapping.
- Method: Match the chosen model specification exactly and preserve the transform from source pixels to model coordinates. Use known color and geometry fixtures, compare host and device preprocessing, and invert padding or crop transforms during output alignment.
- Fixture: A non-square frame with colored corner markers and a bright thin object near the padded boundary.
- Oracle: Host and device tensors agree and the returned depth aligns with the original object position.
- Mutant that must fail: Stretch every input to a square without recording the geometry transform.

Machine-readable fixture: [P099_VERIFY_IMAGE_PREPROCESSING.json](P099_VERIFY_IMAGE_PREPROCESSING.json).

`scripts/gates/p099_verify_image_preprocessing.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p099*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P099-01 through TC-P099-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
