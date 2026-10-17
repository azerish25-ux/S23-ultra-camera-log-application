# P148 — Verify offline privacy and permissions

Active phase: **P148**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Privacy test report and permission inventory". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Privacy test report and permission inventory

- Goal: Make local processing and minimum permission use observable properties.
- Method: Audit network traffic, permission prompts, logging, crash reports, and exported metadata. The default render path must not upload frames, depth maps, faces, or audio. Optional content downloads are explicit and separable from operation after installation.
- Fixture: Airplane-mode capture and development with all model assets installed, plus a diagnostic export.
- Oracle: The workflow succeeds locally and the report omits personal paths and unnecessary identifiers.
- Mutant that must fail: Send image thumbnails to analytics while describing the app as entirely offline.

Machine-readable fixture: [P148_VERIFY_OFFLINE_PRIVACY_AND_PERMISSIONS.json](P148_VERIFY_OFFLINE_PRIVACY_AND_PERMISSIONS.json).

`scripts/gates/p148_verify_offline_privacy_and_permissions.py` records a privacy report only when every permission is `{name, required, used}`, a permission that is used but not required is rejected, network endpoints are empty for an offline claim, and a nonempty `analytics_payload` while `offline_claim` is true is rejected. Camera and microphone may be required only when capture needs them. An unused required permission is recorded as a warning, not hidden. Personal paths and unnecessary identifiers in the diagnostic export are rejected, and the default path must not upload frames, depth maps, faces, or audio. Optional content downloads stay explicit and separable from operation after installation. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p148*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P148-01 through TC-P148-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
