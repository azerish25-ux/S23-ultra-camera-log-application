# P032 — measure physical audiovisual synchronization

Active phase: **P032**. Entry gate: **P031**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for a physical audiovisual protocol and a measured
offset report. It does **not** measure a physical Galaxy S23. A green host run
is not that measurement and is not physical S23 qualification.

## Deliverable

Physical audiovisual protocol and measured offset report.

Machine-readable fixture:
[P032_MEASURE_PHYSICAL_AUDIOVISUAL_SYNCHRONIZATION.json](P032_MEASURE_PHYSICAL_AUDIOVISUAL_SYNCHRONIZATION.json)
(`schemaVersion` 1, `phase` `P032`, `mapId` `s23-physical-av-sync-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is a flash-and-click recording. Geometry is documented at 3400 mm
with a 340000 mm/s sound speed, so sound travel is exactly 10000000 ns. First
video and audio packet timestamps are both `0`. After sound travel is removed,
the beginning and middle events share a 5000000 ns offset and the end event is
15000000 ns. That is a fixed initial error plus 10000000 ns of drift.
Uncertainty on each event is 200000 ns and does not cover either term.

`scripts/gates/p032_measure_physical_audiovisual_synchronization.py` encodes
the phase method, fixture, oracle, and mutant:

- `assess` estimates each visible-audible event independently of container
  starts. `preservedResults` keep the container token, every event token, the
  sound-travel delay, the initial offset, the end offset, and the drift.
- The fixture decision is `sync_failed`, never `qualified` or `allowed`.
  `rejectedClaims` are `initial-sync-error`, `drift`, and
  `container-start-lip-sync`. Reasons name the initial error and the drift
  separately.
- The mutant sole test `matching-first-packets` is `rejected`. Equal first
  packet timestamps do not replace the physical offsets with a zero lip-sync
  result. A test fails if that mutant is implemented as a pass.
- An undocumented distance does not invent a corrected offset. A residual
  inside the reported uncertainty stays `withheld` and is still not a
  lip-sync certificate.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p032*.py' -v
```

The phase test loads the fixture, checks that the initial error stays distinct
from drift, and checks that matching first packet timestamps are not the
synchronization test. Case modules TC-P032-01 through TC-P032-08 are separate
files. This phase module does not call them. The command above runs their
host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- Matching first packet timestamps do not certify lip sync, fixed cadence, or
  a measured audiovisual mapping.
- A sound-travel correction on this fixture is not a field measurement of
  air temperature, microphone distance, or cinema-camera equivalence.
- The report does not claim sensor-derived Log, ten-bit fidelity, or
  film-stock fidelity.
- No Kotlin, Gradle, or workflow sources were changed.
