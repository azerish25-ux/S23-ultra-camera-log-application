# P078 — Protect skin and neutrals without hidden beautification

Active phase: **P078**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Skin-texture evaluation and optional adjustment policy". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Skin-texture evaluation and optional adjustment policy

- Goal: Avoid unwanted image alteration disguised as film fidelity.
- Method: First improve stock and camera calibration rather than masking errors with face-specific smoothing. Any optional skin-aware adjustment must be visible, reversible, temporally stable, and excluded from clean masters. Never alter identity or facial geometry.
- Fixture: Several skin tones under mixed lighting beside neutral and saturated reference objects.
- Oracle: The rendering preserves texture and geometry, with optional adjustments clearly recorded and independently switchable.
- Mutant that must fail: Silently smooth faces to make a film preset appear more flattering.

Machine-readable fixture: [P078_PROTECT_SKIN_AND_NEUTRALS_WITHOUT_HIDDEN_BEAUTIF.json](P078_PROTECT_SKIN_AND_NEUTRALS_WITHOUT_HIDDEN_BEAUTIF.json).

`scripts/gates/p078_protect_skin_and_neutrals_without_hidden_beautif.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p078*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P078-01 through TC-P078-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
