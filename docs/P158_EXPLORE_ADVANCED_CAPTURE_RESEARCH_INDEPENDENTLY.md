# P158 — Explore advanced capture research independently

Active phase: **P158**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Advanced capture experiment and motion-aware acceptance plan". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Advanced capture experiment and motion-aware acceptance plan

- Goal: Investigate multi-frame HDR, alternative RAW modes, and synchronization only as clearly labelled experiments.
- Method: Define source sampling, motion assumptions, exposure differences, merge artifacts, and output lineage. Compare against single-exposure baselines. Multi-frame computational capture must not be presented as a single unmodified sensor exposure or guaranteed dynamic-range increase in every scene.
- Fixture: A moving subject across differently exposed frames used for a computational HDR merge.
- Oracle: The report measures motion artifacts and retained highlight information separately and labels the merge explicitly.
- Mutant that must fail: Advertise merged dynamic range without testing motion or alignment failures.

Machine-readable fixture: [P158_EXPLORE_ADVANCED_CAPTURE_RESEARCH_INDEPENDENTLY.json](P158_EXPLORE_ADVANCED_CAPTURE_RESEARCH_INDEPENDENTLY.json).

`scripts/gates/p158_explore_advanced_capture_research_independently.py` records an advanced capture experiment only when the label is `experimental`. Advertising merged dynamic range (`claims_extra_stops > 0`) without a `motion_alignment` test result is rejected. Multi-frame HDR must report ghosting or alignment error, not hide it. Alternative RAW modes stay unavailable unless a measurement id exists. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

Motion rule: An experiment label must be experimental. Advertising merged dynamic range (claims_extra_stops > 0) without a motion_alignment test result is rejected. Multi-frame HDR must report ghosting or alignment error, not hide it. Alternative RAW modes stay unavailable unless a measurement id exists. The decision is never qualified. Do not claim sensor-derived Log.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p158*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P158-01 through TC-P158-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
