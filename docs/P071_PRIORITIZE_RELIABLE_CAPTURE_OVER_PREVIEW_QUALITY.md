# P071 — prioritize reliable capture over preview quality

Active phase: **P071**. Entry gate: **P070**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for a capture-priority resource scheduler. It does
**not** measure a physical Galaxy S23. A green host run is not that
measurement and is not physical S23 qualification.

## Deliverable

Resource scheduler and capture-priority stress tests.

Machine-readable fixture:
[P071_PRIORITIZE_RELIABLE_CAPTURE_OVER_PREVIEW_QUALITY.json](P071_PRIORITIZE_RELIABLE_CAPTURE_OVER_PREVIEW_QUALITY.json)
(`schemaVersion` 1, `phase` `P071`, `mapId`
`s23-capture-priority-scheduler-fixture`, implementation base
`d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture increases inference load while the camera and encoder approach a
measured timing budget. Degradation order is fixed:

1. `reduce-monitoring`
2. `lower-inference`
3. `pause-effects`
4. `stop-capture` only when a separately documented capture limit is reached

The selected source mode stays `uhd-24` at `3840x2160`. Preview quality
`reduced` is recorded and the preview is visibly degraded. Source cadence
stays intact because the capture limit has not been reached. Stopping capture
on this fixture would be early.

`scripts/gates/p071_prioritize_reliable_capture_over_preview_quality.py`
encodes the phase method, fixture, oracle, and mutant:

- `assess` on the declared path decides `preview_degraded`. `rejectedClaims`
  is empty. `preservedResults` still contain the mode label, both resolutions,
  cadence, the recorded preview quality, and every degradation step.
  `preview_degraded` is not `qualified` and not `allowed`.
- The mutant path `silent-resolution` lowers recording resolution without
  changing the active mode label. It decides `rejected` and adds
  `silent-resolution-drop`. A test fails if that mutant returns
  `preview_degraded`. The same claim is rejected when the document itself
  sets `recordingResolution` below `selectedResolution` while `modeLabel`
  stays `uhd-24`.
- Reaching the documented capture limit with `stop-capture` applied decides
  `capture_stopped`. The mode and recording resolution are unchanged.
- Breaking cadence before that limit, stopping capture early, skipping the
  degradation order, or leaving preview quality unrecorded is `rejected`.
  An idle budget is `withheld`. The inventory is not deleted.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p071*.py' -v
```

The phase test loads the fixture, checks that preview degrades while source
cadence remains intact, and checks that a silent resolution drop does not
keep the mode label. Case modules TC-P071-01 through TC-P071-08 are separate
files. This phase module does not call them. The command above runs their
host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- `preview_degraded` and `capture_stopped` are scheduler labels. They do not
  prove fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock
  fidelity, cinema-camera equivalence, or a measured camera or encoder
  timing budget.
- Lowering recording resolution without changing the active mode label is
  rejected. Hidden source frame drops that keep preview smooth are rejected
  by TC-P071-06.
- No Kotlin, Gradle, or workflow sources were changed.
