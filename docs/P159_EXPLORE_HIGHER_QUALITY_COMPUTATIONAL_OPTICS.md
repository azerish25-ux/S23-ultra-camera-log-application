# P159 — Explore higher-quality computational optics

Active phase: **P159**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Advanced optics research comparison and adoption gate". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Advanced optics research comparison and adoption gate

- Goal: Investigate richer depth, multi-view cues, or research models only after the baseline product is stable.
- Method: Compare real synchronized inputs where available, improved temporal models, and calibrated geometry under explicit resource and privacy limits. Keep the original on-device workflow usable. New models require licensing, conversion, and difficult-scene validation again.
- Fixture: A larger temporal model improving some boundaries but causing memory pressure and unacceptable deferred rendering time.
- Oracle: The decision reports the quality-cost tradeoff rather than replacing the stable path automatically.
- Mutant that must fail: Adopt a larger model solely because its benchmark ranking is higher.

Machine-readable fixture: [P159_EXPLORE_HIGHER_QUALITY_COMPUTATIONAL_OPTICS.json](P159_EXPLORE_HIGHER_QUALITY_COMPUTATIONAL_OPTICS.json).

`scripts/gates/p159_explore_higher_quality_computational_optics.py` records an optics comparison only when adoption follows the measured gate. A model candidate has name, benchmark_rank, baseline_error, candidate_error, and adopted. Adopting solely because rank is better is rejected: adopted true while candidate_error is not lower than baseline_error, or only rank is cited. Adoption requires a measured error improvement and a named limit. Larger model size alone is not a reason. Baseline product stability must be noted; if baseline_stable is false, adoption is rejected. The fixture model improves boundary error but causes memory pressure and unacceptable deferred rendering time, so the stable path stays in place and the quality-cost tradeoff is reported. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p159*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P159-01 through TC-P159-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
