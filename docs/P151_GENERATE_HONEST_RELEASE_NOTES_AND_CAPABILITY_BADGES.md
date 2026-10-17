# P151 — Generate honest release notes and capability badges

Active phase: **P151**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Evidence-driven release notes and claim audit". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Evidence-driven release notes and claim audit

- Goal: Tie every public capability claim to current evidence and documented limits.
- Method: Build release summaries from accepted records, including exact supported tuples and experimental features. Separate software tests from physical qualification. Keep known failures visible and avoid general camera-equivalence or universal-resolution language.
- Fixture: A release with qualified SDR recording, experimental RAW development, and deferred-only depth effects.
- Oracle: The release notes reflect those scopes and do not advertise live RAW cinema capture or universal 8K support.
- Mutant that must fail: Copy aspirational requirements directly into the implemented features list.

Machine-readable fixture: [P151_GENERATE_HONEST_RELEASE_NOTES_AND_CAPABILITY_BADGES.json](P151_GENERATE_HONEST_RELEASE_NOTES_AND_CAPABILITY_BADGES.json).

`scripts/gates/p151_generate_honest_release_notes_and_capability_badges.py` records release notes only when every public claim has `claim_id`, `badge`, `evidence_id` or null, and `limit`. Badges may be unavailable, experimental, or evidenced. Evidenced requires a non-empty evidence_id and a limit string. A claim with evidence_id null must not be in implemented_features. Unavailable must not read as shipped. Copying an aspirational requirement into implemented_features is rejected. The fixture keeps qualified SDR recording evidenced and implemented, experimental RAW development out of implemented_features, and depth effects deferred-only. It does not advertise live RAW cinema capture or universal 8K support. Known failures stay visible. Software tests stay separate from physical qualification. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

Badge rule: Badges may be unavailable, experimental, or evidenced. Evidenced requires a non-empty evidence_id and a limit string. A claim with evidence_id null must not be in implemented_features. Unavailable must not read as shipped. Copying an aspirational requirement into implemented_features is rejected.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p151*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P151-01 through TC-P151-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
