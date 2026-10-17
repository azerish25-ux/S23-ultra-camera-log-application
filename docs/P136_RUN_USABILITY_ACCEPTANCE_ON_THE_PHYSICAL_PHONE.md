# P136 — Run usability acceptance on the physical phone

Active phase: **P136**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Physical usability report and prioritized corrections". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Physical usability report and prioritized corrections

- Goal: Validate real shooting ergonomics rather than relying on static mockups.
- Method: Test outdoor readability, one-handed operation, landscape framing, gloves where relevant, large text, interruptions, and recovery discovery. Observe user tasks and errors. Keep aesthetic preferences separate from measurable task completion and footage safety.
- Fixture: A user starts a take, receives a thermal warning, stops, finds the retained clip, and shares its evidence.
- Oracle: The task completes without hidden controls or ambiguity about whether footage was saved.
- Mutant that must fail: Approve the UI from a desktop screenshot without a real shooting workflow.

Machine-readable fixture: [P136_RUN_USABILITY_ACCEPTANCE_ON_THE_PHYSICAL_PHONE.json](P136_RUN_USABILITY_ACCEPTANCE_ON_THE_PHYSICAL_PHONE.json).

`scripts/gates/p136_run_usability_acceptance_on_the_physical_phone.py` reads a usability report (`session_count`, `device_id`, `measured_on_device`, and `findings`). Approving the UI (`approved` true) from a desktop screenshot (`measured_on_device` false) is rejected. An honest report with `measured_on_device` false and `approved` false is recorded as not run. Findings that claim a physical pass without a device measurement id are rejected. The gate does not invent a shooting workflow result. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p136*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P136-01 through TC-P136-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
