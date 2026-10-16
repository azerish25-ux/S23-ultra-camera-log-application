# P115 — Build a temporal integration reference

Active phase: **P115**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Temporal integration reference and analytic motion fixtures". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Temporal integration reference and analytic motion fixtures

- Goal: Create a controlled motion-blur oracle using known motion and synthetic intermediate samples.
- Method: Integrate radiance over a declared exposure window with normalized weights. Use known moving shapes before optical-flow interpolation. Keep blur in the appropriate linear domain and test how occlusion changes visible contributions during the exposure.
- Fixture: A bright disk moving at constant velocity across a dark background with known subframe positions.
- Oracle: The integrated trail agrees with the reference exposure window and preserves total energy under the defined boundary policy.
- Mutant that must fail: Average display-encoded frames without accounting for transfer or exposure weights.

Machine-readable fixture: [P115_BUILD_A_TEMPORAL_INTEGRATION_REFERENCE.json](P115_BUILD_A_TEMPORAL_INTEGRATION_REFERENCE.json).

A numeric exposure integrates frames `[[0, 0], [2, 4], [0, 0]]` with weights
`[0.25, 0.5, 0.25]` over the inclusive shutter window `[0, 2]`. Each output
sample is `sum(weight[k] * frame[k][i])`, which is `[1, 2]`. Weights sum to 1.
Negative weights are rejected rather than dropped. A non-zero weight on a frame
outside that window is rejected rather than dropped. An independent oracle that
disagrees by more than `1e-9` is rejected. The result keeps the weight list and
the window.

`scripts/gates/p115_build_a_temporal_integration_reference.py` rejects `applyMutant`,
display-encoded averages, unnormalized weights, negative weights, and frames
outside the shutter window. The evidence id stays in `preservedResults`. The
decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p115*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P115-01 through TC-P115-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
