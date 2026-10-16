# P106 — Implement flow-based history reprojection

Active phase: **P106**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "History reprojection module and synthetic flow tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

History reprojection module and synthetic flow tests

- Goal: Align previous depth into current image coordinates before blending temporal information.
- Method: Use explicit flow direction, coordinate scale, valid regions, and source timestamps. Test translation and rotation with synthetic known geometry. Reject invalid reprojections and preserve current-frame evidence where history is unavailable.
- Fixture: A square translating by a known pixel offset with newly revealed background on one side.
- Oracle: The warped history aligns the square while leaving disoccluded pixels invalid rather than filled with stale foreground depth.
- Mutant that must fail: Blend previous and current depth at identical pixel indices without warping.

Machine-readable fixture: [P106_IMPLEMENT_FLOW_BASED_HISTORY_REPROJECTION.json](P106_IMPLEMENT_FLOW_BASED_HISTORY_REPROJECTION.json).

## Reprojection rule

A previous depth sample `{x, y, depth, dx, dy}` is reprojected by its backward flow.
The new position is `(x + dx, y + dy)` in the same pixel coordinates (`COORDINATE_SCALE_PX = 1`).
A landing outside the half-open frame `[0, frame_width) × [0, frame_height)` is **unknown**.
Its depth is not extrapolated. `|flow + reverse_flow| = hypot(dx + rdx, dy + rdy)` above
`FORWARD_BACKWARD_INCONSISTENCY_PX` (1 pixel) is also **unknown**. Those unknowns are not
filled from neighbouring depth and then called measured. Applying previous depth with every
flow vector zero while `motion_px > 0` is rejected as history pasted without flow. A result
without both `prev_timestamp` and `curr_timestamp` is rejected. Decisions are only
`recorded` or `rejected`.

`scripts/gates/p106_implement_flow_based_history_reprojection.py` rejects that pasted history,
neighbour-filled unknowns, and missing source timestamps. The evidence id stays in
`preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p106*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P106-01 through TC-P106-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
