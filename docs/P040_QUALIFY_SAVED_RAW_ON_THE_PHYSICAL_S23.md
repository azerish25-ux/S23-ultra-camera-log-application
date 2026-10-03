# P040 — qualify saved RAW on the physical S23

Active phase: **P040**. Entry gate: **P039**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for measured RAW duration boundaries. It does **not**
measure a physical Galaxy S23. A green host run is not that measurement and
is not physical S23 qualification.

## Deliverable

Physical RAW qualification matrix and retained source fixtures.

Machine-readable fixture:
[P040_QUALIFY_SAVED_RAW_ON_THE_PHYSICAL_S23.json](P040_QUALIFY_SAVED_RAW_ON_THE_PHYSICAL_S23.json)
(`schemaVersion` 1, `phase` `P040`, `mapId` `s23-saved-raw-qualification-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is an authored five-second successful RAW sequence (`raw-five-second`,
measured `5000` ms of `5000` ms) followed by a sixty-second run (`raw-sixty-second`)
that stops under severe thermal pressure at measured `17250` ms. Frame counts
are authored inventory, not a measured cadence. The longer partial take stays
retained. Requested `60000` ms is not written back as the measured duration.
Maximum-resolution experiments stay conditional and are not attempted. A
five-frame still sequence is recorded as a still sequence only.

`scripts/gates/p040_qualify_saved_raw_on_the_physical_s23.py` encodes the phase
method, fixture, oracle, and mutant:

- `assess` reports both measured duration boundaries. `preservedResults` keep
  the gate token, both take tokens (integrity, source completeness, metadata,
  storage bandwidth, thermal state, and lens behaviour), the still token, the
  conditional maximum-resolution token, and `retained-longer` for the partial
  take.
- The fixture decision is `boundaries_reported`, never `qualified` or
  `allowed`. `rejectedClaims` include `endurance-extrapolation`. Reasons name
  the measured `5000` ms and `17250` ms bounds and state that endurance was
  not extrapolated to `60000` ms.
- The mutant basis `five_frame_still` is `rejected`. Five still frames do not
  become sustained RAW video and do not replace the partial take. A test fails
  if that mutant is implemented as a pass.
- A discarded partial take, a maximum-resolution attempt before the lower-cost
  thermal stop, or a failed acquisition or writer gate cannot certify the run.
  Those decisions still keep the take inventory.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p040*.py' -v
```

The phase test loads the fixture, checks that the sixty-second request is not
treated as measured endurance, and checks that a five-frame still sequence is
not sustained RAW video. Case modules TC-P040-01 through TC-P040-08 are
separate files. This phase module does not call them. The command above runs
their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- `boundaries_reported` does not certify sustained RAW video, fixed cadence,
  sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera
  equivalence.
- A five-frame still sequence is not proof of sustained RAW video.
- The thermal stop is a measured bound on this fixture. It is not an endurance
  certificate and it does not authorize a maximum-resolution experiment.
- No Kotlin, Gradle, or workflow sources were changed.
