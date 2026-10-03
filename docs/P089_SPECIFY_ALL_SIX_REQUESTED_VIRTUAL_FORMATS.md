# P089 — Specify all six requested virtual formats

Active phase: **P089**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Virtual-format registry and geometry validation". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Virtual-format registry and geometry validation

- Goal: Represent Super 8, Super 16, standard 35mm, Super 35, five-perforation 65mm, and fifteen-perforation large-format acquisition coherently.
- Method: Use sourced gate definitions when available and explicitly provisional geometry otherwise. Store perforation orientation, image area, crop, and delivery framing separately. A seventy-millimetre exhibition label must not be substituted for an unsourced acquisition gate.
- Fixture: Two large-format recipes sharing a stock but using five-perforation vertical and fifteen-perforation horizontal acquisition models.
- Oracle: The format records differ in geometry while the shared stock identity remains unchanged.
- Mutant that must fail: Assign a different color LUT to each format and omit gate geometry entirely.

Machine-readable fixture: [P089_SPECIFY_ALL_SIX_REQUESTED_VIRTUAL_FORMATS.json](P089_SPECIFY_ALL_SIX_REQUESTED_VIRTUAL_FORMATS.json).

`scripts/gates/p089_specify_all_six_requested_virtual_formats.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p089*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P089-01 through TC-P089-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
