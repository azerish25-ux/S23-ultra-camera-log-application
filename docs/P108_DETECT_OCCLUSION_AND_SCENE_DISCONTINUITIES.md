# P108 — Detect occlusion and scene discontinuities

Active phase: **P108**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Occlusion mask and scene-reset tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Occlusion mask and scene-reset tests

- Goal: Stop invalid temporal history from leaking across new surfaces or cuts.
- Method: Combine flow consistency, depth disagreement, image change, and explicit edit boundaries with documented thresholds. Reset only the relevant state. Keep gradual lighting changes distinct from cuts and test partial occlusions separately from full scene replacement.
- Fixture: A hand crossing a face, a fast pan revealing a new wall, and a hard edit between unrelated clips.
- Oracle: History is rejected in disoccluded areas and reset at the cut without smearing the previous scene.
- Mutant that must fail: Carry temporal state across every clip boundary because timestamps are continuous.

Machine-readable fixture: [P108_DETECT_OCCLUSION_AND_SCENE_DISCONTINUITIES.json](P108_DETECT_OCCLUSION_AND_SCENE_DISCONTINUITIES.json).

## Detection rule

On an ordered list of depth samples, mark a discontinuity where `abs(d[i] - d[i-1]) > threshold`.
Mark an occlusion where the forward-backward flow residual satisfies `abs(dx + rdx) > flow_threshold` or `abs(dy + rdy) > flow_threshold`.
`smoothed=true` on a discontinuous sequence is rejected. Samples marked `unknown` must stay `unknown`; filling them and labelling `measured` is rejected.
`discontinuity_count`, `occlusion_count`, and `unknown_count` are retained on recorded and rejected results.

The fixture documents threshold `0.5` and flow residual threshold `0.25`. A step or residual equal to the threshold is not a mark.

`scripts/gates/p108_detect_occlusion_and_scene_discontinuities.py` records a host observation that detects those events without smearing. It rejects smoothing across a marked discontinuity, an unknown sample filled and labelled measured, history retained in an occluded region, and history carried across an edit boundary because timestamps are continuous. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p108*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P108-01 through TC-P108-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
