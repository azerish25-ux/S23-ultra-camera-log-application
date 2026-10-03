# P074 — Implement an abstract sensitometric reference

Active phase: **P074**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Abstract density reference and response-curve tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Abstract density reference and response-curve tests

- Goal: Create a stable monotonic exposure-to-density baseline before claiming stock fidelity.
- Method: Use a documented toy curve with explicit toe, approximately linear midsection, and shoulder parameters. Test monotonicity, continuity, exposure scaling, and finite behaviour. Label the curve synthetic; it is a mathematical fixture, not a Kodak profile.
- Fixture: A logarithmically spaced exposure wedge spanning shadows, midtones, and highlights.
- Oracle: The density response follows its declared monotonic shape and does not invent detail after source clipping.
- Mutant that must fail: Relabel a generic sigmoid as a measured Vision3 curve.

Machine-readable fixture: [P074_IMPLEMENT_AN_ABSTRACT_SENSITOMETRIC_REFERENCE.json](P074_IMPLEMENT_AN_ABSTRACT_SENSITOMETRIC_REFERENCE.json).

`scripts/gates/p074_implement_an_abstract_sensitometric_reference.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p074*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P074-01 through TC-P074-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
