# P083 — Scale grain by virtual gate and delivery geometry

Active phase: **P083**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Format-aware grain mapping and resolution consistency tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Format-aware grain mapping and resolution consistency tests

- Goal: Keep grain size meaningful when switching among small and large film formats.
- Method: Define grain dimensions in a declared virtual material coordinate system, then map through crop, scan, and output resampling. Test the same material profile across formats and resolutions. Do not confuse larger output resolution with a physically larger negative.
- Fixture: One stock rendered as Super 8, Super 16, Super 35, and fifteen-perforation large format at two delivery sizes.
- Oracle: The apparent grain scale follows the declared gate and sampling model rather than arbitrary preset-specific pixel counts.
- Mutant that must fail: Use a fixed two-pixel grain radius for every virtual format and output resolution.

Machine-readable fixture: [P083_SCALE_GRAIN_BY_VIRTUAL_GATE_AND_DELIVERY_GEOMETR.json](P083_SCALE_GRAIN_BY_VIRTUAL_GATE_AND_DELIVERY_GEOMETR.json).

`scripts/gates/p083_scale_grain_by_virtual_gate_and_delivery_geometr.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p083*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P083-01 through TC-P083-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
