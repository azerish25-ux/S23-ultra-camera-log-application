# P096 — Validate virtual optics against controlled geometry

Active phase: **P096**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Optical validation laboratory and error decomposition". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Optical validation laboratory and error decomposition

- Goal: Establish that the model behaves coherently before comparing it with famous films.
- Method: Use known-distance objects, sharp source capture, controlled point lights, and repeatable focus positions. Compare physical measurements where available and model predictions otherwise. Keep approximation error distinct from depth-estimation error through synthetic perfect-depth tests.
- Fixture: A controlled three-plane scene rendered once with known depths and once with estimated depths.
- Oracle: The report separates lens-rendering defects from depth-estimation failures and does not blame one for the other.
- Mutant that must fail: Evaluate only the complete ML pipeline with no perfect-depth reference.

Machine-readable fixture: [P096_VALIDATE_VIRTUAL_OPTICS_AGAINST_CONTROLLED_GEOME.json](P096_VALIDATE_VIRTUAL_OPTICS_AGAINST_CONTROLLED_GEOME.json).

`scripts/gates/p096_validate_virtual_optics_against_controlled_geome.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p096*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P096-01 through TC-P096-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
