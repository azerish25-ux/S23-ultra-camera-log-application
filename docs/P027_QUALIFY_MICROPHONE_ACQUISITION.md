# P027 — qualify microphone acquisition

Active phase: **P027**. Entry gate: **P026**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes the microphone-acquisition fixture and the host gate that checks it.
It does **not** measure a physical Galaxy S23. A green host run is not that
measurement.

## Deliverable

Audio acquisition contract and blocked-encoder tests.

Machine-readable fixture: [P027_QUALIFY_MICROPHONE_ACQUISITION.json](P027_QUALIFY_MICROPHONE_ACQUISITION.json)
(`schemaVersion` 1, `phase` `P027`, `contractId` `s23-microphone-acquisition-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is two authored observations, not a device probe. A stereo request
is routed to a mono source and the report says one channel. A blocked encoder
stalls while microphone acquisition continues: encoder delay is `240` ms and
missing microphone time is `0` ms. PCM is `pcm_s16le` at `48000` Hz on
`builtin-mic`. The queue limit is `8` frames. Clipping (`5`) and silencing
(`2`) stay on the stereo-to-mono observation. Acquisition is separate from AAC
callbacks. Route policy is explicit `continue`, not invisible drift.

`scripts/gates/p027_qualify_microphone_acquisition.py` encodes the method,
fixture, oracle, and mutant:

- `evaluate` describes actual source channels. Queue occupancy above the limit
  is `queue-limit-exceeded`. Encoder delay that is not separated from a
  microphone gap is `timing-not-distinguished`. A stall that stops acquisition
  is `stall-treated-as-missing-microphone`.
- `assess_acquisition` decides `actual_channels` when every observation reports
  the source channel count, the queue holds, timing is separated, clipping and
  silencing are preserved, AAC callbacks stay separate, and permission is
  granted. `preservedResults` keeps channel counts, the PCM format, the route,
  queue occupancy, both timing figures, and clip and silence counts.
- The decision is `stopped` when permission is denied, acquisition has stopped,
  and the route policy is explicit `stop`.
- The decision is `rejected` when the output reports requested stereo for a
  one-channel source (`requested-stereo-as-actual`). That is the mutant. The
  inventory is not wiped.
- `actual_channels` is a software label for this fixture. It is not
  `qualified` and not `allowed`.

`assess_acquisition` does not call TC-P027-01 through TC-P027-08. Those case
modules are separate host checks.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p027*.py' -v
```

The phase test loads the fixture, checks that the mono source is not reported
as stereo, checks that the blocked encoder is not missing microphone data, and
checks that reporting requested stereo is rejected. That assertion fails if
the mutant is implemented.

## Non-claims

- This fixture and note are not a device probe and not a physical S23
  measurement or qualification.
- The host result does not certify fixed cadence without measured evidence,
  sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera
  equivalence.
- `actual_channels` does not mean a microphone route was measured on hardware.
- Channel counts, queue limits, and encoder delay in the fixture are authored.
  They are not an Android AudioRecord or MediaCodec session.
- No Android or Kotlin sources were changed.
- `docs/evidence/P027-handoff.json` leaves `commit` null. This phase does not
  invent a git revision.
