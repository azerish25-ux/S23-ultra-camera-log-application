# P116 — Evaluate interpolation without hidden hallucination

Active phase: **P116**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Interpolation benchmark and provenance flags". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Interpolation benchmark and provenance flags

- Goal: Use motion interpolation only where it passes explicit scene and confidence tests.
- Method: Compare candidate flow or learned interpolators on owned footage with high-frame-rate references. Inspect occlusions, thin structures, speculars, and repetitive patterns. Avoid cloud generation and store whether intermediate frames were synthesized.
- Fixture: A rotating fan, crossing hands, and a fast moving reflective object with known high-rate reference footage.
- Oracle: Artifacts are quantified and low-confidence intervals can fall back without being presented as original sensor frames.
- Mutant that must fail: Label synthesized intermediate frames as additional native captured frames.

Machine-readable fixture: [P116_EVALUATE_INTERPOLATION_WITHOUT_HIDDEN_HALLUCINATION.json](P116_EVALUATE_INTERPOLATION_WITHOUT_HIDDEN_HALLUCINATION.json).

`scripts/gates/p116_evaluate_interpolation_without_hidden_hallucination.py` linearly interpolates between captured samples and tags every estimated sample `origin=estimated`. An estimated sample submitted as `origin=captured` is rejected as a hidden hallucination. A withheld midpoint residual is reported and is not relabelled captured. Extrapolation outside the captured span is rejected and those samples are not invented. `interpolationFraction=estimated_count/total_count` stays in the result. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p116*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P116-01 through TC-P116-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
