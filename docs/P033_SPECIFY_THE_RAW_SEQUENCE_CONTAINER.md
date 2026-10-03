# P033 — specify the RAW sequence container

Active phase: **P033**. Dependencies: **P009**, **P024**, **P025**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for a bounded, versioned RAW sequence container and
the reader gate that checks it. It does **not** measure a physical Galaxy S23.
A green host run is not that measurement and is not an S23 qualification.

## Deliverable

RAW source specification and hostile-input reader tests.

Machine-readable fixture: [P033_SPECIFY_THE_RAW_SEQUENCE_CONTAINER.json](P033_SPECIFY_THE_RAW_SEQUENCE_CONTAINER.json)
(`schemaVersion` 1, `phase` `P033`, `contractId` `s23-raw-sequence-container-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

This file is a host fixture. It is not a device byte dump and it does not
optimize a writer. The container records file magic `S23RAW01`, schema version
1, route identity, source geometry, CFA, packing, a calibration snapshot id,
and per-frame lengths, timestamps, integrity, and an explicit end state. The
snapshot id is not a measured colour certificate.

The fixture holds three complete tight uint16 frames (64×48, 6144 bytes each)
and then a final record whose declared payload length is 2147483648 with only
128 bytes present. Container end state is `interrupted`. Recovery mode is
`explicit-complete-prefix`. `originalRewritten` is false.

`scripts/gates/p033_specify_the_raw_sequence_container.py` encodes the method,
fixture, oracle, and mutant:

- `bounds_checked_reserve` sums only the complete prefix after rejecting an
  impossible length. It does not allocate the tail's declared length.
- `mutant_declared_reserve` is the rejected mutant: it adds every declared
  payload length before any bound check. `assess_source` does not use it.
- On this fixture `assess_source` decides `prefix_recovered`. `preservedResults`
  keep the three-frame prefix, geometry, route, and `reserved:18432`.
  `rejectedClaims` list `oversized-length` and `truncated-record` separately.
  The original is not rewritten.
- Strict mode on the same tail decides `development_rejected` and still keeps
  the prefix. A rewrite request decides `rejected` with `original-rewritten`.
- `prefix_recovered`, `development_rejected`, `source_intact`, and `rejected`
  are software labels. None of them is `qualified` or `allowed`.

`assess_source` does not call TC-P033-01 through TC-P033-08. Those case
modules are separate host checks for packing, metadata pairing, oversized
headers, interrupted tails, pool saturation, calibration identity, mutation
during development, and stage-rate conflation.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p033*.py' -v
```

The phase test loads the fixture, checks that the complete prefix and the
corrupt tail are reported separately, and checks that the reserved size is
the bounds-checked prefix. That assertion fails if the reader allocates the
arbitrary declared payload length before checking bounds.

## Non-claims

- This fixture and note are a host fixture, not a device probe, not a physical
  S23 measurement, and not a physical S23 qualification.
- The host result does not certify fixed cadence without measured evidence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- `prefix_recovered` does not mean the truncated source is a completed movie,
  a calibrated recording, or a real-time RAW writer.
- Naming `S23RAW01` does not prove byte compatibility with a phone file and
  does not qualify the on-device writer.
- No Android or Kotlin sources were changed.
- `docs/evidence/P033-handoff.json` leaves `commit` null. This phase does not
  invent a git revision.
