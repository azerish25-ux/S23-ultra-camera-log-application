# P129 — Define the camera screen information hierarchy

Active phase: **P129**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Camera screen specification and layout interaction tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Camera screen specification and layout interaction tests

- Goal: Keep recording, source mode, exposure, audio, and warnings visible without overcrowding the viewfinder.
- Method: Separate persistent capture controls from expandable advanced settings. Show requested versus applied values only where meaningful and label provisional information. Design portrait and landscape layouts around stable Record and Stop targets, not a scrolling toolbar.
- Fixture: Landscape mode with large text, a storage warning, microphone meters, and the manual controls panel open.
- Oracle: Record and Stop remain reachable, warnings remain readable, and the viewfinder is not accidentally replaced by settings.
- Mutant that must fail: Place Stop inside a scrollable control list that moves during recording.

Machine-readable fixture: [P129_DEFINE_THE_CAMERA_SCREEN_INFORMATION_HIERARCHY.json](P129_DEFINE_THE_CAMERA_SCREEN_INFORMATION_HIERARCHY.json).

`scripts/gates/p129_define_the_camera_screen_information_hierarchy.py` records three slots plus a warnings list. Capture must include record and stop. Monitoring (scopes and aids) and processing (looks) are optional. `record_in_scroll_only` true is rejected, as is a record or stop control that is missing from capture. A control id present in both capture and processing is rejected. Permission, thermal, and storage warnings stay visible; a severe warning with `warnings_visible` false is rejected. The hierarchy is recorded, never a usability study pass. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p129*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P129-01 through TC-P129-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
