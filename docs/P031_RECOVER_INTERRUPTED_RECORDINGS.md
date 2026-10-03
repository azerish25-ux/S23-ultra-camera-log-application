# P031 — recover interrupted recordings

Active phase: **P031**. Entry gate: **P030**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for cold-start recovery of an interrupted recording.
It does **not** measure a physical Galaxy S23. A green host run is not that
measurement and is not physical S23 qualification.

## Deliverable

Cold-start recovery scanner and interrupted-file fixtures.

Machine-readable fixture:
[P031_RECOVER_INTERRUPTED_RECORDINGS.json](P031_RECOVER_INTERRUPTED_RECORDINGS.json)
(`schemaVersion` 1, `phase` `P031`, `mapId` `s23-interrupted-recording-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is process termination during muxer finalization. The journal at
`takes/take-7/journal.json` records take `take-7`, selected tracks `video` and
`audio`, terminal status `incomplete`, and no completed-journal flag. The only
remnant is nonempty `takes/take-7/partial.mp4` (4096 bytes). Validation cannot
complete. The file is not playable. It is the sole retained copy. Export and
retry are offered. Deletion is not confirmed.

`scripts/gates/p031_recover_interrupted_recordings.py` encodes the phase
method, fixture, oracle, and mutant:

- `assess` exposes the remnant as `unverified`. It does not discard the
  partial file because validation cannot complete, and it does not treat the
  unfinished MP4 as playable. `preservedResults` keep the journal path, take
  metadata, selected tracks, the artefact token, and the explicit export and
  retry offers.
- `apply_policy` with `delete_lacking_completed_journal` is the mutant. The
  decision is `rejected`. The partial path stays in the inventory. Implementing
  that mutant (dropping every file without a completed journal flag) fails the
  host test.
- `request_delete` without confirmation rejects deletion of the sole retained
  copy. Confirmation yields `delete_authorized` and still keeps the inventory
  token. Neither outcome is `qualified` or `allowed`.
- A completed publication journal may be `journal_complete`. That label is a
  software status only.

`assess` does not call TC-P031-01 through TC-P031-08. Those case modules are
separate host checks.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p031*.py' -v
```

The phase test loads the fixture, checks that the nonempty partial file stays
`unverified`, and checks that the mutant would fail because the file is still
retained. Case modules cover at least two repeats each, including cold-start
transitions and the negative controls. The command above runs those host tests
as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe, not a physical S23 measurement, and not a physical S23 qualification.
- Retaining an unfinished MP4 does not make it playable, verified, or a
  successful take.
- `unverified`, `rejected`, `withheld`, `journal_complete`, and
  `delete_authorized` are software labels. None of them is `qualified` or
  `allowed`.
- The host result does not certify fixed cadence without measured evidence,
  sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera
  equivalence.
- No Android, Kotlin, Gradle, or workflow sources were changed.
- `docs/evidence/P031-handoff.json` leaves `commit` null. This phase does not
  invent a git revision.
