# P025 — specify clock domains and epochs

Active phase: **P025**. Entry gate: **P017**, **P024**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for clock-domain types and a timing-evidence schema.
It does **not** measure a physical Galaxy S23. A green host run is not that
measurement and is not physical S23 qualification.

## Deliverable

Clock-domain types and timing evidence schema.

Machine-readable fixture:
[P025_SPECIFY_CLOCK_DOMAINS_AND_EPOCHS.json](P025_SPECIFY_CLOCK_DOMAINS_AND_EPOCHS.json)
(`schemaVersion` 1, `phase` `P025`, `mapId` `s23-clock-domain-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is audio and video timestamps that share the numeric value
`1000000000` and the unit `ns` but come from different domains: sensor, audio
hardware, monotonic system, and encoded presentation. A codec timestamp of `0`
is kept as a different value. No measured mapping is supplied. Every listed
synchronization path is `unverified`.

`scripts/gates/p025_specify_clock_domains_and_epochs.py` encodes the phase
method, fixture, oracle, and mutant:

- Every timestamp is stored with domain and units. Original sensor times stay
  in `preservedResults`.
- `assess` refuses numeric equivalence. The fixture decision is `rejected`,
  never `qualified` or `allowed`. `rejectedClaims` includes
  `numeric-unit-equivalence`. Unsupported paths remain open questions.
- `subtract` does not subtract unrelated domains when both values are
  nanoseconds. The mutant method `subtract_unrelated_nanoseconds` is rejected
  and does not replace the original tokens with a delta.
- `present` may attach a shared take-epoch label only from an identified
  method and retained samples. The original sensor token is kept beside it.

Correspondence uses only `measured_offset` or `documented_epoch` with at least
two retained sample ids. Anything else, including matching units alone, is not
clock equivalence.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p025*.py' -v
```

The phase test loads the fixture, checks that equal nanosecond values across
domains are rejected, and checks that implementing the mutant (subtracting
those values) would fail. Case modules TC-P025-01 through TC-P025-08 are
separate files. This phase module does not call them. The command above runs
their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- Matching nanosecond units do not establish a shared clock, fixed cadence, or
  a measured audiovisual mapping.
- A mapped software offset is not physical synchronization, sensor-derived
  Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- Container packet alignment is not a lip-sync certificate.
- No Kotlin, Gradle, or workflow sources were changed.
