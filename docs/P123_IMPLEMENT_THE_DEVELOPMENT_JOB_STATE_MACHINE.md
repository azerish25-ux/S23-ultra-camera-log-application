# P123 — Implement the development job state machine

Active phase: **P123**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Job reducer and cancellation race tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Job reducer and cancellation race tests

- Goal: Make queued, preparing, rendering, verifying, publishing, cancelled, and failed states explicit.
- Method: Own jobs independently of the screen while respecting Android execution policy. Record resource requirements, current phase, progress confidence, and failure reason. Cancellation is acknowledged only after workers release ownership and retain appropriate partial artifacts.
- Fixture: Cancellation during output verification followed by reopening the development screen.
- Oracle: The job state is consistent, source media remains intact, and a stale worker cannot publish a cancelled result.
- Mutant that must fail: Mark cancellation complete immediately while background workers still own output handles.

Machine-readable fixture: [P123_IMPLEMENT_THE_DEVELOPMENT_JOB_STATE_MACHINE.json](P123_IMPLEMENT_THE_DEVELOPMENT_JOB_STATE_MACHINE.json).

The host reducer does not add preparing, rendering, verifying, or publishing as state names. Those names raise `ValueError`. Legal states are `idle`, `queued`, `running`, `checkpointed`, `failed`, `cancelled`, and `completed`.

Legal transitions, and no others:

```text
idle->queued
queued->running
running->checkpointed
checkpointed->running
running->completed
running->failed
running->cancelled
queued->cancelled
checkpointed->cancelled
checkpointed->failed
```

A transition log is the whole list of states. The decision is `recorded` only when every adjacent step is legal and `terminalState` equals the last entry. `queued->completed` is a skip and is rejected. Cancel from `running` or `queued` must set `sourceRetained` true. `sourceRetained` false on any cancel is rejected. Failure does not delete the source. Cancellation while workers still own output handles is rejected. A stale worker must not publish a cancelled result.

The fixture log is `idle`, `queued`, `running`, `cancelled` with the source retained and workers released. Reopening the development screen does not move that terminal state. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

`scripts/gates/p123_implement_the_development_job_state_machine.py` rejects `applyMutant`, illegal transitions, a skipped `queued->completed`, a terminal mismatch, source loss on cancel or failure, owned output handles, and a stale publish. TC-P123-01 through TC-P123-08 are separate host checks. This phase module does not call them.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p123*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P123-01 through TC-P123-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
