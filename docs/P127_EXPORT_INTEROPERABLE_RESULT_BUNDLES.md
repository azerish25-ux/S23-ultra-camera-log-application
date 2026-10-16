# P127 — Export interoperable result bundles

Active phase: **P127**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Export bundle schema and privacy-preserving share tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Export bundle schema and privacy-preserving share tests

- Goal: Deliver video with the metadata needed to understand and reproduce it.
- Method: Include source lineage, recipe, profile and model identities, timing mapping, color interpretation, calibration status, clipping counts, and verification summary. Redact personal paths and identifiers in shared reports. Keep optional large intermediates separate from the default share bundle.
- Fixture: A LogC3 result shared without its sidecar and a rendered movie result containing private filesystem paths in metadata.
- Oracle: The UI warns about required interpretation information and sanitizes the public report without losing technical provenance.
- Mutant that must fail: Publish private absolute paths or omit essential Log interpretation metadata.

Machine-readable fixture: [P127_EXPORT_INTEROPERABLE_RESULT_BUNDLES.json](P127_EXPORT_INTEROPERABLE_RESULT_BUNDLES.json).

`scripts/gates/p127_export_interoperable_result_bundles.py` requires a bundle manifest with `source_sha256`, `recipe_version_sha256`, `result_sha256`, `color_transfer`, `container`, and `non_claims`. Hashes are 64 lowercase hex. A missing `source_sha256` blocks export and is rejected when `export_allowed` is true. `color_transfer` of `bt709` or `hlg` is rejected when a label or filename says `logc3` or `Log`. `non_claims` must include the literal `not a physical S23 qualification`. Identical hashes are a pass-through copy only when `grade_applied` is false; the same pair with `grade_applied` true is rejected. Private paths and identifiers are redacted in the public report. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p127*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P127-01 through TC-P127-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
