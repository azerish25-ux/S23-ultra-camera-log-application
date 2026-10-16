# P109 — Refine hair and transparent boundaries

Active phase: **P109**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Boundary refinement module and mixed-pixel corpus results". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Boundary refinement module and mixed-pixel corpus results

- Goal: Improve mixed pixels without reducing the problem to a hard person mask.
- Method: Use edge-aware upsampling and optional matting with temporal constraints. Represent partial coverage where justified and separate confidence from opacity. Evaluate hair, glasses, smoke, and motion-blurred edges; avoid facial smoothing as a substitute for segmentation accuracy.
- Fixture: Backlit hair moving against detailed foliage and transparent glasses crossing the face boundary.
- Oracle: The renderer avoids conspicuous sharp cutouts and unstable halos under normal playback.
- Mutant that must fail: Dilate a binary person mask and blur everything outside it uniformly.

Machine-readable fixture: [P109_REFINE_HAIR_AND_TRANSPARENT_BOUNDARIES.json](P109_REFINE_HAIR_AND_TRANSPARENT_BOUNDARIES.json).

## Band rule

Pixels with `confidence < hair_threshold`, or whose class is `hair`, `transparent`, or `glass`, are seeds. Those seeds are the low-confidence boundary samples. Every sample whose index is within radius `band` of a seed becomes an unknown band, not a hard 0/1 matte.

`scripts/gates/p109_refine_hair_and_transparent_boundaries.py` rejects all of the following. The evidence id stays in `preservedResults`. The decision is `recorded` or `rejected`, never `qualified` or `allowed`.

- A hard matte whose hair or transparent values are only 0 or 1.
- An unknown-band sample that is still a hard 0 or 1.
- An unknown-band sample replaced by the foreground colour and then called opaque.
- Unknown coverage, the fraction of seeds that remain unknown, when it is below `minimum_unknown_coverage`.
- A document with `inpaint_glass` true. Colour behind glass is not invented.
- `applyMutant`, the dilated binary person mask with uniform blur outside it.

Coverage uses the seed set as the denominator. A partial matte strictly between 0 and 1, or the token `unknown`, remains unknown only when that sample is not called opaque. Samples outside the band may stay 0 or 1.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p109*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P109-01 through TC-P109-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
