# P149 — Establish thermal and endurance acceptance

Active phase: **P149**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Endurance protocol and configuration-specific operating envelope". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Endurance protocol and configuration-specific operating envelope

- Goal: Use conservative safety policies and measured operating envelopes.
- Method: Run controlled sustained tests across relevant source and render configurations, record ambient conditions and device state, and observe thermal callbacks. Reduce optional preview work first. Severe pressure triggers a controlled stop that preserves footage; do not bypass protections.
- Fixture: A prolonged high-resolution take followed by deferred depth rendering while the phone is already warm.
- Oracle: The app follows its documented limits, retains media, and does not claim unlimited performance from a short cold run.
- Mutant that must fail: Ignore severe thermal status to maintain an advertised frame-rate claim.

Machine-readable fixture: [P149_ESTABLISH_THERMAL_AND_ENDURANCE_ACCEPTANCE.json](P149_ESTABLISH_THERMAL_AND_ENDURANCE_ACCEPTANCE.json).

`scripts/gates/p149_establish_thermal_and_endurance_acceptance.py` records an endurance protocol only when thermal status is one of `none`, `moderate`, `severe`, `critical`, or `unknown`. Severe or critical must set `continue_capture` false or a controlled stop. Ignoring severe thermal to keep an advertised fps (`continue_capture` true and `advertised_fps` claimed) is rejected. An envelope is recorded only with `measured_on_device` true; otherwise it is not a physical pass and the decision stays recorded only if the document says `unavailable`. Do not claim a frame-rate guarantee from a short sample. Optional preview work is reduced before continued capture while the phone is warm. A controlled stop preserves footage. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p149*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P149-01 through TC-P149-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
