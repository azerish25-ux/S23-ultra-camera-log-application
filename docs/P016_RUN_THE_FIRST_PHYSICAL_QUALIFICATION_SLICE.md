# P016 — first physical qualification slice

Active phase: **P016**. Entry gate: **P015**. This host note does not re-run
P015 and does not claim that P015 was freshly certified here.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. The
original material below is an authored host fixture. A green host run is not a
physical Galaxy S23 measurement.

## Host fixture

Machine-readable fixture:
[P016_RUN_THE_FIRST_PHYSICAL_QUALIFICATION_SLICE.json](P016_RUN_THE_FIRST_PHYSICAL_QUALIFICATION_SLICE.json)
(`schemaVersion` 1, `phase` `P016`, `reportId`
`s23-first-physical-slice-fixture`, `hostFixture` true, implementation base
`d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture models one rear route, a conservative advertised configuration, a
controlled sixty-second take, a visible timing event, and audio when supported.
Source and output metadata are marked inspected. Thermal and storage strings
are retained. The modeled output is playable with one missing sample near
thermal escalation. Playback integrity is `playable-with-gap`; cadence is the
separate status `withheld`; the mode is not endurance-certified; and
`framesChecked` is `all`, not `first`.

`scripts/gates/p016_run_the_first_physical_qualification_slice.py`
(`validate_report`, `assess_slice`) enforces the fixture shape:

- A non-sixty-second duration, non-rear route, missing requested audio, missing
  metadata, or an unplayable output is withheld or rejected.
- The first-frame-only mutant is rejected while preserving thermal, storage,
  playback, and cadence observations.
- `enduranceCertified=true` is rejected.
- The fixture decision is never physical qualification.

## Executable physical protocol

The repository now also contains an executable, opt-in physical path. See
[P016 physical execution protocol](P016_PHYSICAL_EXECUTION.md).

`app/src/androidTest/java/com/s23log/probe/P016PhysicalQualificationTest.kt`
uses the existing camera engine to create a device-bound 65-second bundle on a
real `SM-S918*` phone. It is skipped by ordinary emulator CI unless
`p016Physical=true` is supplied. Device-side evidence deliberately leaves full
decode, marker verification, and physical qualification false.

`scripts/p016_physical_qualification.py` then independently binds identities,
fully decodes video and requested audio, recomputes packet cadence, and detects
the offline flash/tone protocol. Only that two-sided process can emit
`qualified_exact_60s_slice`. A cadence gap produces
`slice_retained_cadence_warning` instead of being hidden.

Run the physical protocol from a clean `main` checkout:

```sh
scripts/run_p016_physical_qualification.sh
```

## Test commands

Host fixture and physical-harness contracts:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p016*.py' -v
```

The original phase test loads the authored JSON fixture. The new host tests
exercise revision staleness, first-frame-only rejection, route/geometry/audio
mismatches, marker absence, cadence warning preservation, and the physical
qualification boundary. TC-P016-01 through TC-P016-08 remain independently
represented; passing host tests do not claim that those interventions were run
on a phone.

## Non-claims

- No physical S23 result is committed by this change. A result exists only
  after the physical runner creates a new exact-device bundle and the host
  validator accepts it.
- A host or emulator pass does not certify endurance, unlimited recording,
  higher resolution, fixed cadence without measured evidence, sensor-derived
  Log, ten-bit sensor fidelity, film-stock fidelity, or cinema-camera
  equivalence.
- `slice_reported` and other fixture labels are not supported-recording badges.
- The added Kotlin source is test-only. Production camera, encoder, storage,
  publication, and recovery behavior are unchanged.
