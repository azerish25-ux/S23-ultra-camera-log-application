# P111 — Implement stable focus tracking and pulls

Active phase: **P111**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Focus tracker and deterministic focus-curve tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Focus tracker and deterministic focus-curve tests

- Goal: Make intentional focus motion distinct from model instability.
- Method: Track a selected subject identity with confidence and explicit loss behavior. Smooth focus in a defined coordinate domain, support keyframed pulls, and avoid abrupt target changes when subjects cross. Store focus decisions in the recipe for reproducibility.
- Fixture: Two people cross paths while the selected subject briefly leaves the frame.
- Oracle: The system follows its documented hold or reacquire policy rather than jumping to the nearer face silently.
- Mutant that must fail: Select the nearest detected face independently in every frame.

Machine-readable fixture: [P111_IMPLEMENT_STABLE_FOCUS_TRACKING_AND_PULLS.json](P111_IMPLEMENT_STABLE_FOCUS_TRACKING_AND_PULLS.json).

The pull limiter is `max_distance_per_frame`. `pull_limiter` keeps a one-frame
focus step inside that distance. A one-frame jump larger than the limit, when
the curve is labelled as a smooth pull, is rejected. Focus at time `t` is
linear between the surrounding keys. Past the last key the last distance is
**held**; clamping that claims interpolation is rejected. Confidence below the
threshold holds the last focus and sets state `held` instead of jumping to a
nearer face. Pull duration and the start and end distances stay in the result.

`scripts/gates/p111_implement_stable_focus_tracking_and_pulls.py` rejects
`applyMutant`, a smooth pull that breaks the limiter, interpolation claimed
beyond the keys, and a low-confidence focus jump. The evidence id stays in
`preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p111*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P111-01 through TC-P111-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
