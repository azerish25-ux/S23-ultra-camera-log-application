# P072 — measure full-pipeline performance

Active phase: **P072**. Entry gate: **P071**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for an integrated performance report. It does **not**
measure a physical Galaxy S23. A green host run is not that measurement and
is not physical S23 qualification.

## Deliverable

Integrated performance report and optimization priorities.

Machine-readable fixture:
[P072_MEASURE_FULL_PIPELINE_PERFORMANCE.json](P072_MEASURE_FULL_PIPELINE_PERFORMANCE.json)
(`schemaVersion` 1, `phase` `P072`, `mapId` `s23-full-pipeline-performance-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The report measures capture, copies, inference, rendering, encoding, decoding,
I/O (`io`), and queue occupancy together. The queue stage contributes
occupancy, not the latency sum. Cold-start milliseconds stay on each workflow
and are larger than that workflow's sustained figure. Live and deferred are
listed as different workflows. Sustained rows are warmed up.

The fixture model is `standalone-depth`. Standalone inference is `1.25` ms.
The integrated latency of the latency stages is `92.75` ms. Copies at `46.5` ms
are the bottleneck because `depth-to-render` repeats a format conversion four
times and copies `12582912` bytes. That is not a camera frame rate.

`scripts/gates/p072_measure_full_pipeline_performance.py` encodes the phase
method, fixture, oracle, and mutant:

- `assess` on the integrated path decides `bottleneck_attributed`.
  `rejectedClaims` is empty. `preservedResults` still contain every stage,
  the conversion, both workflows, the integrated sum `92.75`, and the fastest
  kernel `1.25`. `bottleneck_attributed` is not `qualified` and not `allowed`.
- The mutant path `fastest-kernel` computes nothing from the fastest kernel.
  It decides `rejected`, adds `fastest-kernel-extrapolation`, and keeps
  `computed-integrated-ms:92.75`. A test fails if that mutant returns
  `bottleneck_attributed` or rewrites the integrated total to `1.25`.
- Publishing `standalone-inference` or `fastest-kernel` as the frame-rate
  source is `rejected`. A wrong bottleneck, a collapsed live/deferred
  comparison, a discarded cold start, an unwarmed sustained row, or a live
  sustained figure that is not the integrated sum is `rejected` without
  deleting the inventory.
- If neither workflow reports thermal `sustained`, the decision is
  `withheld`. The stage list remains.

Priorities on this fixture are repeated format conversion, memory copies, and
keeping standalone inference off any frame-rate claim.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p072*.py' -v
```

The phase test loads the fixture, checks that the bottleneck is copies rather
than inference, and checks that the fastest-kernel mutant does not become an
end-to-end or camera frame-rate result. Case modules TC-P072-01 through
TC-P072-08 are separate files. This phase module does not call them. The
command above runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- Attributing a host bottleneck does not prove fixed cadence, sensor-derived
  Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- `bottleneck_attributed` is a fixture arithmetic check. It is not a measured
  camera frame rate, a thermal qualification, or an on-device recording.
- Standalone depth-model latency is not a recording frame rate. End-to-end
  performance is not the fastest individual kernel.
- No Kotlin, Gradle, or workflow sources were changed.
