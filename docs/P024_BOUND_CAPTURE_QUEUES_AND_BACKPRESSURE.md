# P024 — bound capture queues and backpressure

Active phase: **P024**. Entry gate: **P023**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes the backpressure fixture and the host gate that budgets queues. It
does **not** measure a physical Galaxy S23. A green host run is not that
measurement.

## Deliverable

Backpressure policies and a bounded-memory stress harness.

Machine-readable fixture: [P024_BOUND_CAPTURE_QUEUES_AND_BACKPRESSURE.json](P024_BOUND_CAPTURE_QUEUES_AND_BACKPRESSURE.json)
(`schemaVersion` 1, `phase` `P024`, `policyId` `s23-backpressure-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is two synthetic conditions, not a camera session. A depth worker
is blocked for several seconds while the source writer stays healthy. Then the
source writer is stalled on purpose. Queues are separate and budgeted in
frames and bytes. Outstanding leases are counted. Source overflow uses
`visible_stop_with_gap`. Preview and inference use `discard_stale`.

`scripts/gates/p024_bound_capture_queues_and_backpressure.py` encodes the
method, fixture, oracle, and mutant:

- Budget queues in bytes and frames. Preview drops and source failure are
  different policies. Source overflow stops capture and records gap evidence.
  Preview and ML may discard stale work without altering source timestamps.
- `assess` decides `policy_holds` when the blocked depth worker only reduces
  monitoring freshness and the stalled source writer stops with a gap.
  Accepted source-frame identities stay in `preservedResults`. Gap identities
  are rejected claims, not silent overwrites.
- `policy_holds` is a software label for this harness. It is not `qualified`
  and not `allowed`.
- A lease count or lease peak past the instrumented limit is `withheld`. The
  frame inventory is kept.
- An unbounded source queue, hidden frame replacement, or a preview policy
  that is not `discard_stale` is `rejected`. Rejection does not wipe the
  inventory.
- The mutant is one unbounded queue shared by source writing, preview, and
  inference. `assess` decides `rejected` with `unbounded-shared-queue`.
  `unbounded_shared_accepts_all` is the mutant behaviour: every frame is kept,
  nothing stops, and no gap is recorded. That behaviour is not `policy_holds`.

`assess` does not call TC-P024-01 through TC-P024-08. Those case modules are
separate host checks. Discovery runs them; this note does not treat that run
as a device session.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p024*.py' -v
```

The phase test loads the fixture, checks that a blocked depth worker only
reduces monitoring freshness, checks that a stalled source writer stops with
gap evidence, and checks that the shared unbounded queue is rejected. That
assertion fails if the mutant is implemented.

## Non-claims

- This fixture and note are a host fixture, not a device probe and not a
  physical S23 measurement or qualification.
- The host result does not certify fixed cadence without measured evidence,
  sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera
  equivalence.
- `policy_holds` is not `qualified` and not `allowed`. It does not measure
  device memory, sensor frames, or a real capture stop.
- Lease peaks in the harness are counters. They are not a memory profile of a
  phone.
- No Android or Kotlin sources were changed.
- `docs/evidence/P024-handoff.json` leaves `commit` null. This phase does not
  invent a git revision.
