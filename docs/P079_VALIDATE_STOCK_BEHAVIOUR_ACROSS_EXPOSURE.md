# P079 — Validate stock behaviour across exposure

Active phase: **P079**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Stock exposure-series benchmark and limitation notes". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Stock exposure-series benchmark and limitation notes

- Goal: Judge an emulation using exposure series rather than one selected attractive still.
- Method: Render bracketed neutral, skin, fabric, foliage, and highlight scenes with fixed finishing. Compare density response, hue stability, noise interaction, and clipping. Keep an independent validation set and report where the approximation diverges from reference material.
- Fixture: A stock interpretation tuned on a correctly exposed portrait but tested several stops under and over that exposure.
- Oracle: The report exposes failures in shadow color and highlight saturation rather than selecting only the best exposure.
- Mutant that must fail: Remove unfavorable exposure brackets from the comparison set.

Machine-readable fixture: [P079_VALIDATE_STOCK_BEHAVIOUR_ACROSS_EXPOSURE.json](P079_VALIDATE_STOCK_BEHAVIOUR_ACROSS_EXPOSURE.json).

`scripts/gates/p079_validate_stock_behaviour_across_exposure.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p079*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P079-01 through TC-P079-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
