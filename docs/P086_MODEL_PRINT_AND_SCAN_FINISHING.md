# P086 — Model print and scan finishing

Active phase: **P086**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Print-scan graph and domain-boundary tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Print-scan graph and domain-boundary tests

- Goal: Make negative rendering, print response, and scan characteristics independently editable.
- Method: Define density-to-transmission conversion, virtual printing exposure, print response, and scanning or display interpretation. Label unmeasured stages as reconstructed. Avoid double inversion or double display transfer, and keep a bypass for inspecting the negative-stage output.
- Fixture: A neutral density wedge processed through negative-only, print, and final delivery branches.
- Oracle: Each branch has a declared domain and the final neutral ordering remains correct without hidden duplicate transforms.
- Mutant that must fail: Apply a negative inversion twice because both the stock and print nodes assume encoded input.

Machine-readable fixture: [P086_MODEL_PRINT_AND_SCAN_FINISHING.json](P086_MODEL_PRINT_AND_SCAN_FINISHING.json).

`scripts/gates/p086_model_print_and_scan_finishing.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p086*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P086-01 through TC-P086-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
