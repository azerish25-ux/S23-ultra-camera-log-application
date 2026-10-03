# P090 — Map captured field of view to virtual lenses

Active phase: **P090**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Field-of-view mapping and framing guidance". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Field-of-view mapping and framing guidance

- Goal: Prevent a selected cinema focal length from implying a different viewpoint or unseen image coverage.
- Method: Use calibrated or explicitly estimated source intrinsics, crop, stabilization transform, and output framing. Derive the compatible virtual focal length from gate and field of view. Clearly mark incompatible lens selections that would require cropping or unavailable wider coverage.
- Fixture: A wide phone capture paired with a long virtual focal-length selection that would require substantial cropping.
- Oracle: The interface shows the crop or rejects unsupported coverage instead of inventing wider scene content.
- Mutant that must fail: Change only the displayed focal length while leaving geometry unexplained.

Machine-readable fixture: [P090_MAP_CAPTURED_FIELD_OF_VIEW_TO_VIRTUAL_LENSES.json](P090_MAP_CAPTURED_FIELD_OF_VIEW_TO_VIRTUAL_LENSES.json).

`scripts/gates/p090_map_captured_field_of_view_to_virtual_lenses.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p090*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P090-01 through TC-P090-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
