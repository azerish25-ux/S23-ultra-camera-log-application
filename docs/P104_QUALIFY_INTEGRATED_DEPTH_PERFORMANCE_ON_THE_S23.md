# P104 — Qualify integrated depth performance on the S23

Active phase: **P104**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Physical inference qualification and live-versus-deferred decision". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Physical inference qualification and live-versus-deferred decision

- Goal: Decide what can run live and what belongs in deferred development.
- Method: Measure latency, memory, energy, thermal state, and boundary quality while capture and preview are active. Test sustained operation, not just a single inference. Record input resolution and inference cadence separately from output video resolution.
- Fixture: A model that runs quickly when isolated but reduces recording stability during a sustained take.
- Oracle: The scheduler chooses a lower-cost preview or deferred-only policy rather than hiding dropped source frames.
- Mutant that must fail: Advertise model inference rate as full-resolution rendered recording rate.

Machine-readable fixture: [P104_QUALIFY_INTEGRATED_DEPTH_PERFORMANCE_ON_THE_S23.json](P104_QUALIFY_INTEGRATED_DEPTH_PERFORMANCE_ON_THE_S23.json).

For each sample, `total_ms = capture_ms + inference_ms + render_ms + encode_ms`.
The frame interval is `1000/fps`. The over-budget fraction is the share of
samples with `total_ms` greater than that interval. On this fixture fps is 24,
so the interval is `1000/24` ms. Totals are 55, 30, 51, 35, and 46 ms, and
three of the five samples are over budget (fraction 0.6). Isolated inference
stays at 3–6 ms and is not a camera frame rate. Dropped-frame count 3 stays in
`preservedResults`. `device` is `s23`, `measured_on_device` is false, and
physical qualification is `unavailable`, so the decision is `recorded`, never
`qualified`.

`scripts/gates/p104_qualify_integrated_depth_performance_on_the_s23.py` rejects
a standalone `inference_ms` camera-fps claim, a physical qualification claim
without a measurement id, live depth under severe thermal or memory, and any
attempt to hide dropped frames. The evidence id stays in `preservedResults`.
The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p104*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P104-01 through TC-P104-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
