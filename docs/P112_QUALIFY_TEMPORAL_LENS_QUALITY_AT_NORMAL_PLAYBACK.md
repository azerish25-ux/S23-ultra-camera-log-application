# P112 — Qualify temporal lens quality at normal playback

Active phase: **P112**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Temporal optics acceptance report and safe default envelope". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Temporal optics acceptance report and safe default envelope

- Goal: Require a whole-clip quality gate before promoting virtual optics from experimental status.
- Method: Use blinded playback comparisons, perfect-depth references, artifact annotations, and per-category severity limits. Evaluate moderate settings first, then more aggressive apertures. Preserve failure clips and do not average catastrophic boundary failures into a flattering mean.
- Fixture: A mixed corpus containing easy portraits and a smaller number of severe hair, reflection, and foreground-occlusion cases.
- Oracle: The release gate separately reports catastrophic failures and restricts settings or scenes that remain unreliable.
- Mutant that must fail: Approve the renderer using selected still frames from the best clips.

Machine-readable fixture: [P112_QUALIFY_TEMPORAL_LENS_QUALITY_AT_NORMAL_PLAYBACK.json](P112_QUALIFY_TEMPORAL_LENS_QUALITY_AT_NORMAL_PLAYBACK.json).

`scripts/gates/p112_qualify_temporal_lens_quality_at_normal_playback.py` records playback at 24 or 30 fps. Flicker is the sample standard deviation of brightness deltas. Edge crawl is the sample standard deviation of edge-energy deltas. Focus-distance variance is reported and is not hidden. A still-frame sharpness number, a sequence shorter than 8 frames, flicker or edge crawl above its declared limit, a severe boundary frame, and a physical-lens claim without `measured_on_device` are rejected rather than averaged into a pass. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p112*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P112-01 through TC-P112-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
