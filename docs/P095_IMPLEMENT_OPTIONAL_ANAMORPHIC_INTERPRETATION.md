# P095 — Implement optional anamorphic interpretation

Active phase: **P095**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Anamorphic mode contract and geometry regression tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Anamorphic mode contract and geometry regression tests

- Goal: Treat anamorphic squeeze, framing, flare, and bokeh as distinct controls rather than one stretch filter.
- Method: Declare whether the source used a physical adapter or a virtual interpretation. Preserve source aspect ratio and avoid double desqueeze. Parameterize oval bokeh and optional flare independently, and label unsupported optical reconstruction honestly.
- Fixture: A clip recorded through a physical anamorphic adapter and an ordinary spherical phone clip.
- Oracle: Each receives the correct geometry path and the ordinary clip is labelled simulated rather than physically anamorphic capture.
- Mutant that must fail: Desqueeze every clip whenever an anamorphic preset is selected.

Machine-readable fixture: [P095_IMPLEMENT_OPTIONAL_ANAMORPHIC_INTERPRETATION.json](P095_IMPLEMENT_OPTIONAL_ANAMORPHIC_INTERPRETATION.json).

`scripts/gates/p095_implement_optional_anamorphic_interpretation.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p095*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P095-01 through TC-P095-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
