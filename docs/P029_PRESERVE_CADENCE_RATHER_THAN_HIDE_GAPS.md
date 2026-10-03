# P029 — preserve cadence rather than hide gaps

Active phase: **P029**. Entry gate: **P028**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for a cadence analyzer and a source-to-output time
mapping. It does **not** measure a physical Galaxy S23. A green host run is
not that measurement and is not physical S23 qualification.

## Deliverable

Cadence analyzer and source-to-output time mapping.

Machine-readable fixture:
[P029_PRESERVE_CADENCE_RATHER_THAN_HIDE_GAPS.json](P029_PRESERVE_CADENCE_RATHER_THAN_HIDE_GAPS.json)
(`schemaVersion` 1, `phase` `P029`, `mapId` `s23-cadence-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is four source frames at timestamps 0, 40, 88, and 120 milliseconds.
Packet order matches presentation order. Intervals are 40 ms, a
forty-eight-millisecond gap, then a 32 ms short interval. Nominal interval is
40 ms and tolerance is 1 ms, so the span divided by the three steps is exactly
40 ms. That average is inside tolerance. No retiming is applied.

`scripts/gates/p029_preserve_cadence_rather_than_hide_gaps.py` encodes the
phase method, fixture, oracle, and mutant:

- `source_intervals` reads original timestamps in packet order. Presentation
  order is a separate inventory token and is not used to recompute intervals.
- `frames_divided_by_duration_would_approve` is the mutant. It looks only at
  frame count and duration. On this fixture it is true. It is not a decision.
- `assess` still reports the 48 ms gap and the later short interval. Decision
  is `cadence_defect`, never `qualified` or `allowed`. `rejectedClaims`
  includes `forty-eight-millisecond-gap` and `frames-divided-by-duration`.
  Every frame token, both orderings, every interval, duration, and count stay
  in `preservedResults`.
- A `constant_frame_rate_development` retiming record may attach mapping
  metadata. `claimNativeCapture` true is `rejected` as
  `retiming-disguised-as-native`. The source gap remains.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p029*.py' -v
```

The phase test loads the fixture, checks that the 48 ms gap is reported while
the average is inside tolerance, and checks that implementing the mutant
(approving from frame count and duration alone) would fail. Case modules
TC-P029-01 through TC-P029-08 are separate files. This phase module does not
call them. The command above runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- An average frame rate inside tolerance is not per-frame cadence, not fixed
  cadence without measured evidence, and not a repaired native capture.
- Named retiming metadata is not native capture, sensor-derived Log, ten-bit
  fidelity, film-stock fidelity, or cinema-camera equivalence.
- Packet order matching presentation order is not a lip-sync certificate.
- No Kotlin, Gradle, or workflow sources were changed.
