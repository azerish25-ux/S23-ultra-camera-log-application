# P124 — Checkpoint temporal rendering safely

Active phase: **P124**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Resume manifest and uninterrupted-equivalence tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Resume manifest and uninterrupted-equivalence tests

- Goal: Resume expensive work without changing the visual result at the restart boundary.
- Method: Checkpoint verified chunks and relevant temporal state with source, graph, model, profile, and algorithm hashes. Validate complete files before resuming. Recompute overlap where required and ensure final assembly contains each output frame exactly once.
- Fixture: A stopped render resumed after the depth model file has been replaced with a different version.
- Oracle: The old checkpoint is rejected or a new job is created; mixed-model output is never silently assembled.
- Mutant that must fail: Validate a checkpoint only by its output filename and frame number.

Machine-readable fixture: [P124_CHECKPOINT_TEMPORAL_RENDERING_SAFELY.json](P124_CHECKPOINT_TEMPORAL_RENDERING_SAFELY.json).

A checkpoint has `frame_index` (int >= 0), `recipe_sha256`, `partial_output_sha256`,
and `source_sha256`. Resume starts at `frame_index+1`. The published chain ends
at frame 2, so the resume index is 3. That document does not call resume: the
depth model hash changed, a new job id was created, and `resume_frame` 0 is not
treated as a resume of frame 2. Calling resume with `resume_frame` 0 while
`frame_index` > 0 is rejected.

The next checkpoint `frame_index` must be greater than the previous one. The
gap at frame 1 is allowed because `missing_frames` lists it. A silent gap is
rejected. Recipe hashes stay stable inside one job. A mid-job recipe change
without a new job id is rejected. An empty partial output hash is rejected.
Each checkpoint source hash must match the job source. Final assembly contains
each intended output frame exactly once.

`scripts/gates/p124_checkpoint_temporal_rendering_safely.py` rejects `applyMutant`,
a zero resume of a later checkpoint, silent gaps, recipe drift, empty partials,
and source or model mismatches. The evidence id stays in `preservedResults`. The
decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p124*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P124-01 through TC-P124-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
