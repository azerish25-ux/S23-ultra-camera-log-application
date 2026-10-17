# P152 — Run the production readiness review

Active phase: **P152**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Production readiness dossier and signed-off decision record". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Production readiness dossier and signed-off decision record

- Goal: Make a deliberate release decision based on critical risks and complete workflows.
- Method: Review footage retention, crash recovery, color signalling, temporal artifacts, licensing, privacy, accessibility, and update safety. Resolve or explicitly defer noncritical issues. A critical data-loss or misleading-capture defect blocks release regardless of visual quality.
- Fixture: A visually excellent build that occasionally deletes the only staging copy after a failed publication.
- Oracle: The release is blocked until preservation is fixed and regression evidence exists.
- Mutant that must fail: Waive a critical data-loss issue because promotional footage looks convincing.

Machine-readable fixture: [P152_RUN_THE_PRODUCTION_READINESS_REVIEW.json](P152_RUN_THE_PRODUCTION_READINESS_REVIEW.json).

`scripts/gates/p152_run_the_production_readiness_review.py` records a production readiness dossier only when the release rule holds. A dossier lists risks with severity `critical`, `major`, or `minor` and status `open`, `accepted`, or `closed`. An open critical risk blocks release (release_decision must be hold). Waiving a critical data-loss issue (severity critical, status accepted, reason looks_convincing or empty) is rejected. Release go is recorded only when no open critical risks remain and the decision cites the risk ids. Promotional footage is not evidence. Preservation must be fixed and regression evidence must exist before a go. Visual quality cannot waive a data-loss gate. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p152*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P152-01 through TC-P152-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
