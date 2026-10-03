# P028 — implement two-track startup and drain

Active phase: **P028**. Entry gate: **P027**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes the two-track mux fixture and the host gate that checks startup and
drain. It does **not** measure a physical Galaxy S23. A green host run is not
that measurement.

## Deliverable

Two-track mux protocol and EOS fault tests.

Machine-readable fixture: [P028_IMPLEMENT_TWO_TRACK_STARTUP_AND_DRAIN.json](P028_IMPLEMENT_TWO_TRACK_STARTUP_AND_DRAIN.json)
(`schemaVersion` 1, `phase` `P028`, `contractId` `s23-two-track-startup-drain-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is one synthetic take. The video format arrives immediately, two
video samples are pending, the audio format arrives later, then Stop occurs
before audio EOS. Video EOS lands inside the 1500 ms drain bound. Partial
output is `private-stage/take-p028.mp4`. No audio sample is fabricated.

`scripts/gates/p028_implement_two_track_startup_and_drain.py` encodes the
method, fixture, oracle, and mutant:

- Wait for every selected track format before starting the muxer.
- Pre-start samples are bounded (`maxPreStartSamples` 3). EOS is per track.
- Maximum drain duration is `maxDrainDurationMs`.
- `assess_mux` decides `unverified_partial` when a selected track misses EOS
  inside that bound. `preservedResults` keeps the partial output, the take id,
  both selected tracks, and `failed:audio`.
- `protocol_complete` is a host label only when every selected format arrived
  before mux start, both tracks reach EOS inside the bound, and audio was not
  fabricated. It is not `qualified` and not `allowed`.
- The mutant (`muxPolicy` `start-on-first-track`) is `rejected` with claim
  `mux-started-on-first-track`. Later selected tracks stay in the inventory.
  Fabricated audio, a blown pre-start bound, and `wait-forever` drain are
  rejected as well.

`assess_mux` does not call TC-P028-01 through TC-P028-08. Those case modules
are separate host checks. Discovery runs them; this note does not treat that
run as a device session.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p028*.py' -v
```

The phase test loads the fixture, checks that Stop happens before audio EOS,
and checks that starting the muxer on the first track is rejected. That
assertion fails if the mutant is implemented.

## Non-claims

- This fixture and note are not a device probe and not a physical S23
  measurement or qualification.
- The host result does not certify fixed cadence without measured evidence,
  sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera
  equivalence.
- `unverified_partial` and `protocol_complete` are software labels for this
  fixture. They are not a verified recording and not an on-device mux.
- No Android or Kotlin sources were changed.
- `docs/evidence/P028-handoff.json` leaves `commit` null. This phase does not
  invent a git revision.
