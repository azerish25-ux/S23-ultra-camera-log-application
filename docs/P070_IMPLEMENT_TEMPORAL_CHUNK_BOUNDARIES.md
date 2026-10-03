# P070 — implement temporal chunk boundaries

Active phase: **P070**. Entry gate: **P069**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for temporal chunk boundaries. It does **not** measure
a physical Galaxy S23. A green host run is not that measurement and is not
physical S23 qualification.

## Deliverable

Temporal chunk contract and uninterrupted-versus-resumed tests.

Machine-readable fixture:
[P070_IMPLEMENT_TEMPORAL_CHUNK_BOUNDARIES.json](P070_IMPLEMENT_TEMPORAL_CHUNK_BOUNDARIES.json)
(`schemaVersion` 1, `phase` `P070`, `mapId` `s23-temporal-chunk-boundaries-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is a subject crossing a chunk boundary during a focus pull, with a
process restart at the boundary. `temporal-denoise` declares history `4` and
lookahead `2`, checkpoints that state, and binds its cache to the source,
model, graph, and algorithm identities. Chunk 0 emits frames 0–3 and reads
lookahead frames 4–5 without emitting them. Chunk 1 reloads overlap frames 2–3
and emits frames 4–7 once. Uninterrupted and resumed runs both report frame
count 8. Resumed continuity `0.006` is inside tolerance `0.01`, the checkpoint
is loaded, and the resumed model is not an empty state.

`scripts/gates/p070_implement_temporal_chunk_boundaries.py` encodes the phase
method, fixture, oracle, and mutant:

- `assess` on the checkpointed path decides `continuity_preserved`. That label
  is a host comparison of fixture numbers. It is not `qualified` and not
  `allowed`.
- The mutant path `empty-restart` restarts the temporal model from an empty
  state at every export chunk. It decides `rejected` with
  `empty-state-restart` and keeps the same chunk, frame, and identity
  inventory. A test fails if that mutant returns `continuity_preserved`.
- A resumed record that already says `emptyState` is `rejected` on the
  checkpointed path as well.
- Overlap frames copied into the final output, a scene cut that keeps history,
  history cleared without a cut, an unbound or mismatched cache, a short
  lookahead, a missing checkpoint, a continuity delta over tolerance, or a
  frame count other than 8 are `rejected`. The inventory stays.
- A scene cut that invalidates history can still decide `continuity_preserved`
  when the frame count and tolerance still hold.
- If the focus pull, the boundary crossing, or the boundary restart was not
  recorded, the decision is `withheld` and the chunks remain.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p070*.py' -v
```

The phase test loads the fixture, checks uninterrupted-versus-resumed
continuity and the exact frame count, and checks that an empty-state restart
does not count as continuity. Case modules TC-P070-01 through TC-P070-08 are
separate files. This phase module does not call them. The command above runs
their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- `continuity_preserved` does not prove fixed cadence, sensor-derived Log,
  ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- It is not a measured resumed export, a focus-pull capture, or a cinema-camera
  temporal model.
- Restarting from an empty state at every chunk is not accepted continuity.
- No Kotlin, Gradle, or workflow sources were changed.
