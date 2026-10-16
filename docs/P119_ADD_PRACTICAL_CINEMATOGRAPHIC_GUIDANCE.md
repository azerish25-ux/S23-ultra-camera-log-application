# P119 — Add practical cinematographic guidance

Active phase: **P119**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Capture guidance rules and nonintrusive UI tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Capture guidance rules and nonintrusive UI tests

- Goal: Help the user obtain suitable source footage instead of relying on postprocessing to conceal capture failures.
- Method: Provide optional guidance for exposure, focus, source sharpness, clipping, framing, and virtual-lens compatibility. Separate advice from automatic changes. Do not change physical camera position or lighting claims through software labels.
- Fixture: A heavily clipped face and a virtual shallow-focus recipe selected for a physically out-of-focus source.
- Oracle: The app explains the source limitations and preserves user control rather than promising restoration.
- Mutant that must fail: Hide clipping warnings whenever a cinematic preset is active.

Machine-readable fixture: [P119_ADD_PRACTICAL_CINEMATOGRAPHIC_GUIDANCE.json](P119_ADD_PRACTICAL_CINEMATOGRAPHIC_GUIDANCE.json).

Guidance is a list of statements. Each statement is bound to a measured limit
with `fps`, `shutter_angle` (maximum degrees that mode supports),
`max_stable_motion_px`, and `mode_available`.

The recorded mode `mode-48` measures `fps=48`, `shutter_angle=172.8`, and
`max_stable_motion_px=6`. Exposure at that limit is
`172.8 / 360 / 48 = 0.01` seconds. A 180-degree shutter at the same fps would
be `180 / 360 / 48 = 0.0104166666667` seconds, which the mode does not support.
The statement "this mode cannot do 180 degrees at this fps" is recorded.
Clipping and out-of-focus limits are explained, and the words do not promise
restoration. A cinematic preset may be active only while clipping warnings stay
visible. Advice does not change settings, camera position, or lighting labels.

A statement with `limitId` null, such as "raise the shutter to 180 degrees",
is rejected as ungrounded guidance. The evidence id stays in `preservedResults`.
Recommending shutter `180` or fps `24` on `mode-48` is rejected. Promises of
film-stock fidelity, ARRI equivalence, or sensor-derived Log are rejected.
Saying the mode cannot do 180 degrees when `shutter_angle` is already 180 is
rejected. Motion above `max_stable_motion_px` that is called stable is rejected.

`scripts/gates/p119_add_practical_cinematographic_guidance.py` rejects `applyMutant`
and a cinematic preset that hides clipping warnings. The decision is never
`qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p119*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P119-01 through TC-P119-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
