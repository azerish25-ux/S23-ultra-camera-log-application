# P016 — first physical qualification slice

Active phase: **P016**. Entry gate: **P015**. This host note does not re-run
P015 and does not claim that P015 was freshly certified here.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes an authored host fixture for one exact configuration report. It does
**not** measure a physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Physical qualification report for one exact configuration, represented here as
a host fixture only.

Machine-readable fixture:
[P016_RUN_THE_FIRST_PHYSICAL_QUALIFICATION_SLICE.json](P016_RUN_THE_FIRST_PHYSICAL_QUALIFICATION_SLICE.json)
(`schemaVersion` 1, `phase` `P016`, `reportId` `s23-first-physical-slice-fixture`,
`hostFixture` true, implementation base
`d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture models one rear route, the conservative advertised configuration,
a controlled sixty-second take, a visible timing event, and audio because
audio is marked supported. Source and output metadata are marked inspected.
Thermal and storage strings are retained. The modeled output is playable with
one missing sample near thermal escalation. Playback integrity is
`playable-with-gap`. Cadence is the separate status `withheld`. The mode is
not endurance-certified. `framesChecked` is `all`, not the first frame.

`scripts/gates/p016_run_the_first_physical_qualification_slice.py`
(`validate_report`, `assess_slice`) enforces that shape:

- Method: choose one actually available rear route and conservative advertised
  configuration; capture a controlled sixty-second take with a visible timing
  event and audio when supported; decode it fully; inspect source and output
  metadata; preserve thermal and storage observations.
- Fixture story: a real phone take with a single missing sample near thermal
  escalation and an otherwise playable output. The JSON file is an authored
  stand-in for that story. It is not a captured phone file.
- Oracle: the file is retained, playback integrity and cadence receive
  separate statuses, and the mode is not endurance-certified. The host
  decision for that record is `slice_reported`. It is never `qualified` or
  `allowed`.
- Mutant: accept a mode after checking only the first decoded frame.
  `firstFrameOnly` true (`framesChecked` `first`) is decision `rejected`
  with claim `first-frame-only`. Thermal, storage, playback, and cadence
  observations stay in `preservedResults`.
- `enduranceCertified` true is rejected. A non-sixty-second duration, a
  non-rear route, missing audio when audio is supported, or missing metadata
  is `withheld`. An unplayable output is rejected. None of those paths clear
  the stored observations.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p016*.py' -v
```

The phase test loads the JSON fixture, checks the separate playback and
cadence statuses, checks that the slice is not endurance-certified, and checks
that a first-frame-only mutant is rejected. Case modules `p016_tc01.py`
through `p016_tc08.py` are loaded by their own tests. This phase module does
not execute those case modules.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- **TC-P016-01 through TC-P016-08 are separate modules. The phase module did
  not run those modules.** No result from those modules is claimed here.
- A host pass does not certify endurance, unlimited recording, higher
  resolution, fixed cadence without measured evidence, sensor-derived Log,
  ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- `slice_reported` and `operational` are software labels for the fixture.
  They are not a supported-recording badge and not physical qualification.
- No Kotlin or Android sources were changed.
