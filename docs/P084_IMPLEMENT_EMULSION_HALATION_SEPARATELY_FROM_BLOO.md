# P084 — Implement emulsion halation separately from bloom

Active phase: **P084**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Halation model, kernel tests, and controlled-light benchmark". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Halation model, kernel tests, and controlled-light benchmark

- Goal: Create a controlled material scattering model instead of outlining all bright objects in red.
- Method: Operate from the appropriate pre-display signal, use bounded multi-scale kernels, and preserve energy accounting under the chosen approximation. Separate stock-related color weighting from lens or filter bloom. Include broad highlights, edges, and isolated emitters in validation.
- Fixture: A bright white window, a narrow colored point light, and an ordinary pale surface at moderate exposure.
- Oracle: Halation follows the declared intensity and spatial model without creating identical red borders on every pale object.
- Mutant that must fail: Apply a red edge detector to the final display image and call it halation.

Machine-readable fixture: [P084_IMPLEMENT_EMULSION_HALATION_SEPARATELY_FROM_BLOO.json](P084_IMPLEMENT_EMULSION_HALATION_SEPARATELY_FROM_BLOO.json).

`scripts/gates/p084_implement_emulsion_halation_separately_from_bloo.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p084*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P084-01 through TC-P084-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
