# P130 — Implement source and look selection separately

Active phase: **P130**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host reference for "Separated control model and truthfulness UI tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Separated control model and truthfulness UI tests

- Goal: Prevent users from confusing capture capability with a virtual film format.
- Method: Use distinct selectors for physical source mode, virtual format, stock, lens interpretation, and finishing recipe. Show computational cost and calibration status where relevant. Changing a look must not silently alter recording resolution or source lineage.
- Fixture: Selecting an IMAX-style recipe while the active source is a qualified 1080p SDR mode.
- Oracle: The interface preserves and displays the source mode while labelling the large-format appearance as simulated.
- Mutant that must fail: Rename the active recording mode IMAX 70mm after a preset selection.

Machine-readable fixture: [P130_IMPLEMENT_SOURCE_AND_LOOK_SELECTION_SEPARATELY.json](P130_IMPLEMENT_SOURCE_AND_LOOK_SELECTION_SEPARATELY.json).

`scripts/gates/p130_implement_source_and_look_selection_separately.py` keeps a selection's `source_id`, `source_sha256`, and `source_transfer` apart from `look_id` and `look_params`. Changing the look, including look parameters only, leaves that source triple unchanged. If a look change alters any source field, the result is rejected and the committed source identity stays in `preservedResults`. A look name containing `log` or `LogC3` must not rewrite `source_transfer`. Relabel of `bt709` or `hlg` into `logc3` via the look is rejected. Source and look are both required fields: applying a look with no source is rejected. Clearing the look (`look_id` null) keeps the source and is recorded only while `source_retained` stays true; it must not delete source bytes. The IMAX-style recipe on the qualified 1080p SDR source is labelled simulated. Renaming the recording mode to IMAX 70mm is rejected. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p130*.py' -v
```

## Non-claims

- This is an authored host reference, not a device probe and not a physical S23 measurement.
- It does not certify sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P130-01 through TC-P130-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
