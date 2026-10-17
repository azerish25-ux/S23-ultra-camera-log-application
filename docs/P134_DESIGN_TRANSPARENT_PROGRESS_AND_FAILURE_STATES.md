# P134 — Design transparent progress and failure states

Active phase: **P134**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host reference for "Progress semantics and failure-state screenshots/tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Progress semantics and failure-state screenshots/tests

- Goal: Tell users what is happening without fabricated percentages or vague success banners.
- Method: Progress should identify capture, inference, rendering, verification, or publication. Use indeterminate states when remaining work is unknown. Errors distinguish unsupported mode, unavailable model, source corruption, output failure, and retained recoverable footage.
- Fixture: A render reaches its final frame but still requires full decode verification and gallery publication.
- Oracle: The UI does not show completed until acceptance and publication policy are satisfied.
- Mutant that must fail: Show one hundred percent success immediately after the last frame is submitted to the encoder.

Machine-readable fixture: [P134_DESIGN_TRANSPARENT_PROGRESS_AND_FAILURE_STATES.json](P134_DESIGN_TRANSPARENT_PROGRESS_AND_FAILURE_STATES.json).

`scripts/gates/p134_design_transparent_progress_and_failure_states.py` records progress as either indeterminate or `accounted_frames/expected_frames`. The fraction cannot be 1.0 until `drain_complete` is true and every frame is accounted. When the last frame has been submitted but encode drain is still open, the ratio would be 1.0 and is withheld: the state stays indeterminate rather than inventing a percentage. Showing 100 percent when `drain_complete` is false is rejected. When `expected_frames` is 0 the state is indeterminate; a displayed percentage is rejected. A failure must include a non-empty reason and `success` false. A success banner with a failure reason is rejected. Accepted completion still waits until verification and publication are both satisfied. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p134*.py' -v
```

## Non-claims

- This is an authored host reference, not a device probe and not a physical S23 measurement.
- It does not certify sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P134-01 through TC-P134-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
