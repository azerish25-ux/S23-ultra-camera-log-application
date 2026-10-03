# P068 — implement synchronization and ownership barriers

Active phase: **P068**. Entry gate: **P067**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for GPU resource ownership and delayed completion.
It does **not** measure a physical Galaxy S23. A green host run is not that
measurement and is not physical S23 qualification.

## Deliverable

GPU resource owner and delayed-completion tests.

Machine-readable fixture:
[P068_IMPLEMENT_SYNCHRONIZATION_AND_OWNERSHIP_BARRIERS.json](P068_IMPLEMENT_SYNCHRONIZATION_AND_OWNERSHIP_BARRIERS.json)
(`schemaVersion` 1, `phase` `P068`, `mapId`
`s23-synchronization-ownership-fixture`, implementation base
`d4deac8fc82832fd23396a01065c5f0bf9da6670`).

Each frame carries an identity, a generation, and a lifetime. The pool slot
is `texture-pool-0`. In-flight work is bound to `2`. Correctness
synchronization is recorded apart from performance measurements.
`performanceMeasured` is false on the fixture and is never a fence.

The fixture is one slow GPU frame followed by rapid cancellation and a reuse
attempt on the same slot:

- `slow-gpu` is generation `1`, submitted, still in flight, cancelled, and
  only partially written. The fence is not complete, so cancellation does
  not release the slot.
- `next-frame` is generation `2` and tries to read that slot. Partial and
  previous-generation data stay blocked.

`scripts/gates/p068_implement_synchronization_and_ownership_barriers.py`
encodes the phase method, fixture, oracle, and mutant:

- `assess` on the fenced path decides `rejected`. `rejectedClaims` are
  `partial-read` and `previous-generation`. `preservedResults` still contain
  the slot, both frames, `payload=slow-partial`, and `payload=next-clean`.
  `rejected` is not `qualified` and not `allowed`.
- The mutant path `immediate-recycle` recycles the texture as soon as the
  command is submitted. It still decides `rejected`, adds
  `immediate-recycle`, and does not erase the partial or previous-generation
  claims. A test fails if that mutant returns `completion_verified` or
  `ownership_held`.
- A later read after a completed, non-partial fence decides
  `completion_verified` on the fenced path. The same document on the mutant
  path stays `rejected`.
- Releasing a cancelled frame before the fence, exceeding the in-flight
  bound, or treating a performance measurement as a fence is `rejected`.
  No submission is `withheld`. Holding a cancelled in-flight frame without
  a reader is `ownership_held`. Frames are not deleted.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p068*.py' -v
```

The phase test loads the fixture, checks that the next frame cannot read
the slow partial generation, and checks that immediate recycle after
submission does not free the slot. Case modules TC-P068-01 through
TC-P068-08 are separate files. This phase module does not call them. The
command above runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- Rejecting a host reuse does not prove fixed cadence, sensor-derived Log,
  ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- `completion_verified` and `ownership_held` are fixture decisions. They are
  not a measured GPU fence, a hidden stall turned into a frame rate, or an
  on-device recording claim.
- Recycling a texture immediately after command submission is not accepted.
- No Kotlin, Gradle, or workflow sources were changed.
