# P081 — Establish deterministic grain coordinates

Active phase: **P081**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Grain seed contract and render-order invariance tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Grain seed contract and render-order invariance tests

- Goal: Make texture reproducible across tiles, resolutions, retries, and rendering order.
- Method: Use an explicit take seed and frame identity with global image or virtual-gate coordinates. Counter-based randomness avoids dependence on thread scheduling. Define whether a retimed repeated frame shares its original grain or receives a new simulated exposure; record that policy.
- Fixture: The same frame rendered as one image, many tiles, and a resumed job using the same recipe.
- Oracle: Grain placement agrees under the declared deterministic contract and never repeats a tile-local pattern.
- Mutant that must fail: Reseed the random generator from wall-clock time for every tile.

Machine-readable fixture: [P081_ESTABLISH_DETERMINISTIC_GRAIN_COORDINATES.json](P081_ESTABLISH_DETERMINISTIC_GRAIN_COORDINATES.json).

`scripts/gates/p081_establish_deterministic_grain_coordinates.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p081*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P081-01 through TC-P081-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
