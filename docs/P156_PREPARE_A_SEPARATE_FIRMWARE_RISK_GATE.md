# P156 — Prepare a separate firmware risk gate

Active phase: **P156**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Firmware authorization checklist and stop conditions". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Firmware authorization checklist and stop conditions

- Goal: Require explicit authorization and a device-specific safety plan before irreversible changes.
- Method: Document model variant, bootloader state, verified backups, recovery images, rollback limits, security consequences, and potential permanent state changes. A general request to build an app does not authorize flashing. Keep ordinary development operational without firmware changes.
- Fixture: A proposed flash with an unverified image and no confirmed recovery route for the exact device variant.
- Oracle: The gate remains closed and the directive continues with non-destructive app work.
- Mutant that must fail: Proceed because another phone with a similar name accepted the image.

Machine-readable fixture: [P156_PREPARE_A_SEPARATE_FIRMWARE_RISK_GATE.json](P156_PREPARE_A_SEPARATE_FIRMWARE_RISK_GATE.json).

`scripts/gates/p156_prepare_a_separate_firmware_risk_gate.py` records a firmware authorization checklist. Authorization requires `device_serial`, `image_digest`, a `user_authorized` bool, and nonempty `stop_conditions`. Proceeding because another phone with a similar name accepted the image (`similar_name_only` true) is rejected. `user_authorized` false means do not proceed and is recorded as blocked. Missing stop conditions is rejected. A general request to build an app does not authorize flashing. This gate does not authorize flashing; it only records whether the checklist is complete. Even a complete checklist leaves `flashAuthorized` false and the gate closed. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p156*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P156-01 through TC-P156-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
