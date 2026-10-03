# P041 — define the calibrated profile contract

Active phase: **P041**. Dependencies: **P007**, **P033**, **P040**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for a profile schema and a provenance-aware importer.
It does **not** measure a physical Galaxy S23. A green host run is not that
measurement and is not physical S23 qualification.

## Deliverable

Profile schema and provenance-aware importer.

Machine-readable fixture:
[P041_DEFINE_THE_CALIBRATED_PROFILE_CONTRACT.json](P041_DEFINE_THE_CALIBRATED_PROFILE_CONTRACT.json)
(`schemaVersion` 1, `phase` `P041`, `mapId` `s23-calibrated-profile-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture holds two profiles. `labelled-measured-no-refs` carries the author
assertion `measured` and an empty measurement-reference list. `synthetic-physical`
is category `synthetic` and is offered for physical footage. Both numerical
payloads are finite. Their SHA-256 payload hashes are stored on the profiles
and are not a certificate.

`scripts/gates/p041_define_the_calibrated_profile_contract.py` encodes the
phase method, fixture, oracle, and mutant:

- `assess` hashes the complete numerical payload (matrix, direction, white
  point, exposure scale, crop, and black model). Nonfinite tokens and hash
  mismatches are rejected. `preservedResults` keep every profile token, the
  author assertion, and the computed hash.
- The author assertion stays separate from importer status. A measured label
  without measurement references is `rejected-unreferenced` and is retained for
  exploratory research. It is not certified.
- A synthetic profile offered for physical footage is refused as physical
  calibration. The fixture decision is `rejected`, never `qualified`,
  `allowed`, or `certified`.
- Manufacturer-derived profiles stay `provisional`. A referenced measured
  record may be `measurement_record` on this host and is still not certified.
- The mutant `promote_measured_string` is `rejected` with
  `measured-string-to-certified`. A test fails if that mutant is implemented
  as a pass.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p041*.py' -v
```

The phase test loads the fixture, checks that the unreferenced measured label
and the synthetic physical offer are refused, and checks that a measured
string is not certified. Case modules TC-P041-01 through TC-P041-08 are
separate files. This phase module does not call them. The command above runs
their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- An author string `measured` does not certify a profile. A synthetic profile
  is not physical calibration. A manufacturer-derived profile is not a
  measured profile.
- The host record does not claim fixed cadence, sensor-derived Log, ten-bit
  fidelity, film-stock fidelity, or cinema-camera equivalence.
- No Kotlin, Gradle, or workflow sources were changed.
