# P076 — Model channel interaction conservatively

Active phase: **P076**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Channel-coupling model and stability tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Channel-coupling model and stability tests

- Goal: Add color response beyond independent tone curves while preserving explicit assumptions.
- Method: Define whether channel coupling acts on exposure, density, or reconstructed transmission. Fit or tune with held-out references, constrain instability, and separate creative saturation from material response. Document that RGB input cannot uniquely recover the original spectrum.
- Fixture: Neutral exposures and strongly saturated lights that stress cross-channel response.
- Oracle: Neutral behaviour remains controlled, saturated inputs stay finite, and unsupported spectral fidelity is not claimed.
- Mutant that must fail: Apply an arbitrary color matrix after every stage and call the result spectral simulation.

Machine-readable fixture: [P076_MODEL_CHANNEL_INTERACTION_CONSERVATIVELY.json](P076_MODEL_CHANNEL_INTERACTION_CONSERVATIVELY.json).

`scripts/gates/p076_model_channel_interaction_conservatively.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p076*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P076-01 through TC-P076-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
