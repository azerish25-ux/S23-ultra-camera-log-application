# P097 — Define the depth-provider interface

Active phase: **P097**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Depth provider contract and stale-result tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Depth provider contract and stale-result tests

- Goal: Make depth semantics, confidence, geometry, and latency explicit at the model boundary.
- Method: Return model identity, units, coordinate transform, valid region, confidence policy, source timestamp, and processing status with each depth field. Support unavailable or stale results. Keep inference independent of camera ownership and prohibit a depth result from modifying source evidence.
- Fixture: A depth map computed for an earlier cropped frame arriving after the current preview has changed orientation.
- Oracle: The consumer detects the mismatched timestamp and geometry instead of applying the map to the wrong image.
- Mutant that must fail: Return only a float array with no source identity or coordinate metadata.

Machine-readable fixture: [P097_DEFINE_THE_DEPTH_PROVIDER_INTERFACE.json](P097_DEFINE_THE_DEPTH_PROVIDER_INTERFACE.json).

`scripts/gates/p097_define_the_depth_provider_interface.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p097*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P097-01 through TC-P097-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
