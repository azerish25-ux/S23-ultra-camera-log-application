# P037 — build the bounded saved-source writer

Active phase: **P037**. Entry gate: **P036**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for a bounded RAW writer. It does **not** measure a
physical Galaxy S23. A green host run is not that measurement and is not
physical S23 qualification.

## Deliverable

Bounded RAW writer and deterministic overflow harness.

Machine-readable fixture:
[P037_BUILD_THE_BOUNDED_SAVED_SOURCE_WRITER.json](P037_BUILD_THE_BOUNDED_SAVED_SOURCE_WRITER.json)
(`schemaVersion` 1, `phase` `P037`, `writerId` `s23-bounded-raw-writer-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture pauses the source writer, offers four owned copies into a pool of
three, stops the capture controller, resumes the writer, then offers one late
record. Policy is `stop_on_full_pool`. Flush policy is `flush_on_stop`. A short
write of 128 bytes is recorded and does not rewrite timestamps or digests.

`scripts/gates/p037_build_the_bounded_saved_source_writer.py` encodes the
method, fixture, oracle, and mutant:

- Owned copies move through the fixed-capacity pool to an independent writer.
  Source count, flush policy, short writes, and overflow are recorded.
- A full pool stops acquisition. Older frames are not overwritten and
  timestamps are not invented.
- `assess` decides `overflow_visible` when `r0`, `r1`, and `r2` stay ordered
  and intact, `r3` is visible overflow, and late `r4` cannot resume the failed
  take. `overflow_visible` is not `qualified` and not `allowed`.
- A pool that never overflows is `withheld`. A missing flush policy is
  `rejected`. The record inventory stays in `preservedResults`.
- The mutant policy `overwrite_oldest_keep_green` is `rejected` with
  `overwrite-oldest-keep-green`. `mutant_overwrite` is the bad behaviour: the
  oldest frame is dropped and the indicator stays green. That behaviour is not
  `overflow_visible`.

`assess` does not call TC-P037-01 through TC-P037-08. Those case modules are
separate host checks.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p037*.py' -v
```

The phase test loads the fixture, checks that retained records stay ordered,
checks that overflow stays visible, checks that late completion cannot resume
the failed take, and checks that the overwrite-oldest mutant is rejected. That
assertion fails if the mutant is implemented.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- The host result does not certify fixed cadence without measured evidence,
  sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera
  equivalence.
- `overflow_visible` is not `qualified` and not `allowed`. It does not measure
  device storage, sensor frames, or a real capture stop.
- Short-write counts in the harness are scripted. They are not a disk profile
  of a phone.
- No Android, Kotlin, Gradle, or workflow sources were changed.
