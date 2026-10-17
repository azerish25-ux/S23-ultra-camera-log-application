# P154 — Survey public firmware and HAL information

Active phase: **P154**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Non-destructive architecture research report". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Non-destructive architecture research report

- Goal: Research the device architecture without modifying the user’s phone.
- Method: Inspect official architecture documentation, available source releases, public logs, and lawful device diagnostics. Record exact model and firmware applicability. Separate kernel source availability from access to proprietary camera processing components.
- Fixture: A public source package that lacks the proprietary imaging component needed for the proposed change.
- Oracle: The report records the missing component rather than claiming the source package is a complete camera firmware implementation.
- Mutant that must fail: Assume publishing a kernel source tree exposes every camera algorithm and sensor mode.

Machine-readable fixture: [P154_SURVEY_PUBLIC_FIRMWARE_AND_HAL_INFORMATION.json](P154_SURVEY_PUBLIC_FIRMWARE_AND_HAL_INFORMATION.json).

`scripts/gates/p154_survey_public_firmware_and_hal_information.py` records a survey only when each source has `url`, a `public` bool, and `documents` stating what that source actually documents. `phone_modified` must be false. Assuming a kernel source tree exposes every camera mode (`claims_all_modes` true) is rejected. A source that is not public cannot be used as evidence. Architecture notes may be recorded only as unverified against the user's phone. The public fixture records the missing `proprietary-imaging-component` and does not call the source package a complete camera firmware implementation.

A kernel source tree does not prove every camera algorithm, every sensor mode, proprietary camera processing components, or behavior on the user's phone. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p154*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P154-01 through TC-P154-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
