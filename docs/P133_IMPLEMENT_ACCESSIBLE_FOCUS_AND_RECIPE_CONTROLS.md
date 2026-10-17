# P133 — Implement accessible focus and recipe controls

Active phase: **P133**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Accessibility interaction tests and semantic control audit". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Accessibility interaction tests and semantic control audit

- Goal: Make visual editing possible without relying solely on tiny unlabeled gestures.
- Method: Provide accessible names, state descriptions, keyboard or switch navigation where applicable, and numeric alternatives for ROIs and focus controls. Do not convey failure only through color. Preserve focus order across panels and orientation changes.
- Fixture: A screen-reader user selects a grey-reference ROI, changes virtual focus, and cancels a development job.
- Oracle: All actions have usable labels and state feedback, and cancellation remains available without a precision gesture.
- Mutant that must fail: Expose a custom control only as an unlabeled canvas.

Machine-readable fixture: [P133_IMPLEMENT_ACCESSIBLE_FOCUS_AND_RECIPE_CONTROLS.json](P133_IMPLEMENT_ACCESSIBLE_FOCUS_AND_RECIPE_CONTROLS.json).

`scripts/gates/p133_implement_accessible_focus_and_recipe_controls.py` audits every control for an id, a non-empty `accessible_name`, a role, and a non-gesture path (`button`, `slider`, or `stepper`). A control that is only an unlabeled canvas (`accessible_name` empty, or role `canvas` with no name) is rejected. Focus order must include `record` and `stop`. Minimum target size is reported; a size below 48 with no alternative labeled control in the same group is rejected. Recipe controls stay on the recipe panel and do not share a group or panel with capture controls. ROI and focus controls need a numeric slider or stepper. Cancellation stays on a labeled non-gesture control, and failure is not conveyed only through color. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p133*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P133-01 through TC-P133-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
