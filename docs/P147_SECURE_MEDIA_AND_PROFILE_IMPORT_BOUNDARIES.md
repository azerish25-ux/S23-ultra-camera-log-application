# P147 — Secure media and profile import boundaries

Active phase: **P147**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Import threat model and parser fuzz corpus". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Import threat model and parser fuzz corpus

- Goal: Treat external files, archives, LUTs, models, and profiles as hostile until validated.
- Method: Bound lengths, dimensions, nesting, decompression, and allocation before use. Validate paths and hashes, restrict URI grants, and keep native parsers current. Reject nonfinite matrices and dangerous archive paths. Fuzz parsers with retained minimal reproducers.
- Fixture: A profile containing NaN, a huge declared image dimension, and an archive path attempting parent traversal.
- Oracle: All inputs fail safely without excessive allocation, file escape, or source corruption.
- Mutant that must fail: Trust extension names and allocate according to unvalidated headers.

Machine-readable fixture: [P147_SECURE_MEDIA_AND_PROFILE_IMPORT_BOUNDARIES.json](P147_SECURE_MEDIA_AND_PROFILE_IMPORT_BOUNDARIES.json).

`scripts/gates/p147_secure_media_and_profile_import_boundaries.py` records an import only when kind is media, archive, lut, model, or profile, magic matches the extension (or its canonical signature), `header_validated` is true, `declared_size` matches `actual_size` within 0, and no path contains `../`. Trusting the extension while magic disagrees is rejected. Allocating from an unvalidated header (`header_validated` false) is rejected. Zip/archive path traversal (`../`) is rejected. A validated import with matching magic, size, and no traversal is recorded. The fuzz corpus keeps the NaN profile, the huge declared image dimension, and the parent-traversal archive, and those inputs stay rejected without excessive allocation, file escape, or source corruption. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p147*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P147-01 through TC-P147-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
