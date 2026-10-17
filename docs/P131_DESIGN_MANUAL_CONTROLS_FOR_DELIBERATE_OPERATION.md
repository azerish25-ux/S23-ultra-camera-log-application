# P131 — Design manual controls for deliberate operation

Active phase: **P131**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host reference for "Manual interaction contract and draft-state tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Manual interaction contract and draft-state tests

- Goal: Offer precise adjustment without accidental changes during a take.
- Method: Provide bounded sliders, numeric entry, reset, and explicit apply behavior where needed. Keep units visible and disable unavailable controls with reasons. Distinguish draft values from committed effective targets and observed sensor results.
- Fixture: A user types an invalid shutter value, rotates the phone, and then returns to the controls.
- Oracle: The invalid draft is not applied, valid state survives appropriately, and the source recording configuration remains unchanged.
- Mutant that must fail: Apply every partially typed numeric string immediately to the camera.

Machine-readable fixture: [P131_DESIGN_MANUAL_CONTROLS_FOR_DELIBERATE_OPERATION.json](P131_DESIGN_MANUAL_CONTROLS_FOR_DELIBERATE_OPERATION.json).

`scripts/gates/p131_design_manual_controls_for_deliberate_operation.py` keeps a draft string apart from the applied number. The applied value changes only on explicit submit of a complete finite number inside the inclusive advertised range. Partial strings such as `1.` and `""` do not change the applied value. Submitting a complete number outside that range is rejected and leaves the previous applied value. Record and Stop stay enabled. Setting `apply_partial` true, which applies every keystroke, is rejected. Reset restores the advertised reset value and ignores the draft. An unavailable control stays disabled only with a reason and cannot move the applied value. The draft does not rewrite the source recording configuration or the observed sensor result. After rotation, the invalid shutter draft is still unapplied. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p131*.py' -v
```

## Non-claims

- This is an authored host reference, not a device probe and not a physical S23 measurement.
- It does not certify sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P131-01 through TC-P131-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
