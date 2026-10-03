# P075 — Build data ingestion for sensitometry

Active phase: **P075**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Sensitometry importer and unit-consistency checks". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Sensitometry importer and unit-consistency checks

- Goal: Import licensed response measurements without confusing plot axes, densities, or exposure conventions.
- Method: Capture units, reference exposure, measurement conditions, channel interpretation, and digitization uncertainty. Validate monotonic intervals and interpolation behaviour. Retain raw measurement points separately from fitted coefficients and never overwrite original data.
- Fixture: A curve table with reversed log-exposure order and one point copied in linear exposure units.
- Oracle: The importer flags inconsistent axes before producing a stock profile.
- Mutant that must fail: Fit all numeric columns without inspecting their physical meaning.

Machine-readable fixture: [P075_BUILD_DATA_INGESTION_FOR_SENSITOMETRY.json](P075_BUILD_DATA_INGESTION_FOR_SENSITOMETRY.json).

`scripts/gates/p075_build_data_ingestion_for_sensitometry.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p075*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P075-01 through TC-P075-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
