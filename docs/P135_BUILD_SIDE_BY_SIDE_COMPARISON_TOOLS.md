# P135 — Build side-by-side comparison tools

Active phase: **P135**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Comparison viewer and synchronized playback tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Comparison viewer and synchronized playback tests

- Goal: Help users judge real improvements with matched inputs and controllable viewing.
- Method: Provide synchronized playback, split views, exposure-consistent comparisons, effect bypass, and recipe metadata. Avoid comparing different moments or differently scaled thumbnails. Allow inspecting clean source and processed output without accidental double transforms.
- Fixture: Two renders of the same clip with different duration mappings and different display transforms.
- Oracle: The comparison aligns time explicitly and makes differing transforms visible rather than implying a fair matched test.
- Mutant that must fail: Compare unrelated frames and automatically boost one version’s contrast.

Machine-readable fixture: [P135_BUILD_SIDE_BY_SIDE_COMPARISON_TOOLS.json](P135_BUILD_SIDE_BY_SIDE_COMPARISON_TOOLS.json).

`scripts/gates/p135_build_side_by_side_comparison_tools.py` compares a left side and a right side. Each side has `source_sha256`, `frame_index`, `transfer`, and `contrast_boost`. Both source hashes and frame indexes must match; mismatched frames are rejected. `contrast_boost` must be 1. Both transfers must be declared. The synchronized playback offset must be 0 unless an explicit offset is disclosed. Automatic contrast boost is rejected. Differing duration mappings and display transforms stay visible and are not treated as a fair matched test. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

Match rule: both source hashes and frame indexes must match; mismatched frames are rejected; contrast_boost must be 1; both transfers must be declared; sync offset must be 0 unless explicitly disclosed; automatic contrast boost is rejected.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p135*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P135-01 through TC-P135-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
