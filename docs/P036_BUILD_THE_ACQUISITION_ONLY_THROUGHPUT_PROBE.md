# P036 — build the acquisition-only throughput probe

Active phase: **P036**. Entry gate: **P035**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for an acquisition-only throughput probe. It does
**not** measure a physical Galaxy S23. A green host run is not that measurement
and is not physical S23 qualification.

## Deliverable

Acquisition probe and stage-separated throughput report.

Machine-readable fixture:
[P036_BUILD_THE_ACQUISITION_ONLY_THROUGHPUT_PROBE.json](P036_BUILD_THE_ACQUISITION_ONLY_THROUGHPUT_PROBE.json)
(`schemaVersion` 1, `phase` `P036`, `mapId` `s23-acquisition-throughput-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is one route. Discarded acquisition-only frames use equal 10000000 ns
intervals (regular cadence, sustained `100/1` per second) and `framesRetained`
false. The same bound written to storage uses unequal intervals (lost cadence,
sustained `40/3`) with frames retained. Encoded counters are empty. Four
preallocated buffers bound the run. Publication is `separated`.

`scripts/gates/p036_build_the_acquisition_only_throughput_probe.py` encodes the
phase method, fixture, oracle, and mutant:

- Intervals, occupancy, and copy time are counters. Sustained delivery is
  computed from those intervals. It is not a field the fixture may invent.
- `assess` keeps every stage token. Acquisition-only frames are stated as not
  retained. The fixture decision is `withheld`, never `qualified` or `allowed`.
- `recording_rate` returns `withheld` for that fixture. It does not return
  `100/1`.
- Publication `acquisition_as_recording` is the mutant. It is `rejected`.
  `rejectedClaims` includes `acquisition-as-recording`. The recording token
  stays `recordingCapability:withheld`, and the saved-source token remains.

A saved stage that actually retained frames on a regular cadence may be named
`recordingCapability:saved_source:<rate>`. That label is `stage_separated`, not
a recorded-RAW certificate and not the discard rate.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p036*.py' -v
```

The phase test loads the fixture, checks that the regular discard rate stays
apart from the slower storage stage, and checks that implementing the mutant
(publishing `100/1` as recording capability) would fail. Case modules
TC-P036-01 through TC-P036-08 are separate files. This phase module does not
call them. The command above runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- The acquisition-only rate is not reliable recorded RAW video, saved-source
  throughput, or final encoded performance.
- A host pass does not certify fixed cadence without measured evidence,
  sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera
  equivalence.
- `retained_path` and `stage_separated` are software labels. They are not
  `qualified` or `allowed`.
- No Kotlin, Gradle, or workflow sources were changed.
