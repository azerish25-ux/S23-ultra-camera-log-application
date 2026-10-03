# P063 — validate editor interoperability

Active phase: **P063**. Entry gate: **P062**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for editor import guidance. It does **not** measure a
physical Galaxy S23 and it does **not** run an external editor. A green host
run is not that measurement and is not physical S23 qualification.

## Deliverable

Editor round-trip report and import guidance.

Machine-readable fixture:
[P063_VALIDATE_EDITOR_INTEROPERABILITY.json](P063_VALIDATE_EDITOR_INTEROPERABILITY.json)
(`schemaVersion` 1, `phase` `P063`, `mapId` `s23-editor-interoperability-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture export is LogC3, AWG3 primaries, LogC3 transfer, video range, in a
Main10 container. Import instructions say to use video levels and the sidecar.
`independent-decoder` `1.4.2` is recorded twice: once at video levels
(`video-levels`, manual assignment) and once with an incorrect full-range
assumption (`full-range`). Automatic recognition is not claimed and was not
tested. The sidecar restates video range, AWG3, and LogC3. A generic player
version `unmeasured` opens the file from a thumbnail only. That open is
inventory, not a pass. The supported workflow statement is video-level LogC3
with the explicit sidecar.

`scripts/gates/p063_validate_editor_interoperability.py` encodes the phase
method, fixture, oracle, and mutant:

- `assess` on `detect-mismatch` decides `mismatch_recorded`. `rejectedClaims`
  is `incorrect-full-range`. `preservedResults` keep the export, both imports,
  the sidecar, the consumer version, and the workflow statement.
  `mismatch_recorded` is not `qualified`, not `allowed`, and not
  `interoperable`.
- The mutant interpretation `player-opens` decides `rejected` with
  `generic-player-open` first, even though `opening_would_approve_interoperability`
  is true. The same inventory is kept. A test fails if that mutant is
  implemented as `interoperable`, `qualified`, `allowed`, or `mismatch_recorded`.
- A missing workflow, a sidecar contradiction, or an untested automatic
  recognition claim is `rejected`. Aligning both imports to video levels is
  `withheld`. File opening is not interoperability.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p063*.py' -v
```

The phase test loads the fixture, checks that the full-range assumption is a
tonal mismatch against the video-level export, and checks that the mutant is
rejected. Case modules TC-P063-01 through TC-P063-08 are separate files. This
phase module does not call them. The command above runs their host tests as
well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe, not an editor round trip on a workstation, and not a physical S23
  measurement or qualification.
- Detecting a range mismatch does not establish sensor-derived Log, ten-bit
  fidelity, film-stock fidelity, cinema-camera equivalence, or fixed cadence
  without measured evidence.
- A generic player opening the file, or a thumbnail, does not certify color
  interpretation or automatic recognition.
- No Kotlin, Gradle, or workflow sources were changed.
