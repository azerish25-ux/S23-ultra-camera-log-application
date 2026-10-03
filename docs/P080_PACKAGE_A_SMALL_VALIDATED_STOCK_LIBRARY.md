# P080 — Package a small validated stock library

Active phase: **P080**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Initial versioned stock pack and profile acceptance report". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Initial versioned stock pack and profile acceptance report

- Goal: Prioritize a few coherent profiles over an unverified catalogue of hundreds.
- Method: Select initial daylight, tungsten, and monochrome interpretations based on available evidence and rights. Freeze profile IDs, add preview thumbnails rendered from owned fixtures, and document calibration status. Require regression renders for every later update.
- Fixture: A profile update improving one reference scene while breaking a neutral exposure wedge.
- Oracle: The update is blocked or released as a distinct experimental profile rather than silently replacing the stable default.
- Mutant that must fail: Update all presets in place without rendering regression fixtures.

Machine-readable fixture: [P080_PACKAGE_A_SMALL_VALIDATED_STOCK_LIBRARY.json](P080_PACKAGE_A_SMALL_VALIDATED_STOCK_LIBRARY.json).

`scripts/gates/p080_package_a_small_validated_stock_library.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p080*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P080-01 through TC-P080-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
