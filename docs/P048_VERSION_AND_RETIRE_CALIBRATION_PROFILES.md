# P048 — version and retire calibration profiles

Active phase: **P048**. Entry gate: **P047**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for profile versioning, rollback, and comparison.
It does **not** measure a physical Galaxy S23. A green host run is not that
measurement and is not physical S23 qualification.

## Deliverable

Profile lifecycle manager and reproducibility tests.

Machine-readable fixture:
[P048_VERSION_AND_RETIRE_CALIBRATION_PROFILES.json](P048_VERSION_AND_RETIRE_CALIBRATION_PROFILES.json)
(`schemaVersion` 1, `phase` `P048`, `mapId` `s23-profile-lifecycle-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is an authored catalog. `prof-v1` is the approved profile for
firmware `fw-1-0-0` and lens route `logical0-main`. `take-archived` and
`export-archived` (`recipe-archived`) keep that reference and content hash.
`prof-v2` is a newly measured candidate on firmware `fw-2-0-0`. `export-revised`
(`recipe-revised`) is an explicit new render. It does not replace
`recipe-archived`. Migration policy is `new-development-version`.

Compatibility keys are exact: `firmware|lensRoute|versionId`. A firmware or
lens-route change does not retarget an older source. Rollback changes status
only. Comparison reads two retained hashes and does not write provenance.

`scripts/gates/p048_version_and_retire_calibration_profiles.py` encodes the
phase method, fixture, oracle, and mutant:

- `assess` reopens the archived take on its original key. The fixture decision
  is `reproducible`, never `qualified` or `allowed`.
- `install_revision` appends a version and leaves historical exports in place.
- `rollback` restores a retained version to `approved` without rewriting
  recipes.
- `compare` reports whether two versions differ.
- `replace_in_place=True`, or a profile whose bytes changed under an identifier
  an export still records, is the mutant. The decision is `rejected`. Recorded
  recipes and hashes stay in `preservedResults`.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p048*.py' -v
```

The phase test loads the fixture, checks that the earlier recipe remains
reproducible beside a new revision, and checks that implementing the mutant
(replacing profile bytes while keeping the old version identifier) would fail.
Case modules TC-P048-01 through TC-P048-08 are separate files. This phase
module does not call them. The command above runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- `reproducible` is a host binding between fixture hashes. It is not physical
  S23 capture, fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock
  fidelity, or cinema-camera equivalence.
- A candidate profile is not a measured colour profile and is not an in-place
  replacement of an archived export.
- Rollback and comparison do not certify a camera, a lens, or a firmware build.
- No Kotlin, Gradle, or workflow sources were changed.
