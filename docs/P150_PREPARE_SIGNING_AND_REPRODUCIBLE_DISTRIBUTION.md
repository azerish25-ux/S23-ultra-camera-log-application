# P150 — Prepare signing and reproducible distribution

Active phase: **P150**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Release signing plan and update preservation tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Release signing plan and update preservation tests

- Goal: Separate debug convenience from a maintainable release and update process.
- Method: Use owner-controlled signing, pinned dependencies, reproducible source records, and explicit version migration tests. Keep secrets outside the repository. Verify installation and update without losing private sources, profiles, recipes, or recovery records.
- Fixture: An update from an earlier signed release containing private RAW sources and a pending render job.
- Oracle: The update preserves compatible data and handles migration explicitly; signing mismatch is not solved by silently uninstalling user data.
- Mutant that must fail: Recommend uninstalling the previous app without warning about private footage loss.

Machine-readable fixture: [P150_PREPARE_SIGNING_AND_REPRODUCIBLE_DISTRIBUTION.json](P150_PREPARE_SIGNING_AND_REPRODUCIBLE_DISTRIBUTION.json).

`scripts/gates/p150_prepare_signing_and_reproducible_distribution.py` records a release plan only when `build_type` is `debug` or `release`, `signing` is `debug`, `upload`, or `none`, and `update_preserves_private_footage` is a bool. Recommending uninstall without a footage-loss warning (`warns_footage_loss` false while `recommends_uninstall` true) is rejected. Debug signing must not be labelled a production update. Release with signing none is rejected as not reproducible for users. The same source revision must be recorded (`recorded_source_revision` equals `source_revision`). Private footage preservation false on an update is rejected. Upload signing is the owner-controlled production key. Secrets stay outside the repository. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Update rule

A release plan has build_type debug or release, signing debug, upload, or none, and update_preserves_private_footage bool. Recommending uninstall without a footage-loss warning (warns_footage_loss false while recommends_uninstall true) is rejected. Debug signing must not be labelled a production update. Release with signing none is rejected as not reproducible for users. The same source revision must be recorded. Private footage preservation false on an update is rejected.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p150*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P150-01 through TC-P150-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
