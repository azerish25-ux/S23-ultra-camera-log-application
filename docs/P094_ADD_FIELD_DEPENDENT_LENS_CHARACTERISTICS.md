# P094 — Add field-dependent lens characteristics

Active phase: **P094**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Lens-character profile schema and continuity tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Lens-character profile schema and continuity tests

- Goal: Model cat-eye bokeh, vignetting, aberration, and breathing only with explicit provenance and limits.
- Method: Separate geometric defocus from field-dependent appearance. Parameterize position, wavelength or channel approximation, focus changes, and exposure effects. Distinguish measured lens profiles from creative profiles. Test edge cases near the frame boundary and extreme focus values.
- Fixture: Off-axis highlights during a gradual focus pull with vignetting and longitudinal color effects enabled.
- Oracle: The effects change continuously and remain within their declared model rather than jumping between arbitrary presets.
- Mutant that must fail: Apply fixed chromatic offsets independent of depth and call them a calibrated lens.

Machine-readable fixture: [P094_ADD_FIELD_DEPENDENT_LENS_CHARACTERISTICS.json](P094_ADD_FIELD_DEPENDENT_LENS_CHARACTERISTICS.json).

`scripts/gates/p094_add_field_dependent_lens_characteristics.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p094*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P094-01 through TC-P094-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
