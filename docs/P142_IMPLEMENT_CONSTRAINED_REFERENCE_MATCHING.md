# P142 — Implement constrained reference matching

Active phase: **P142**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Parameter suggestion prototype and structure-preservation tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Parameter suggestion prototype and structure-preservation tests

- Goal: Use optional analysis to suggest renderer parameters without replacing source content.
- Method: Analyze approved reference material for broad color, tone, texture, and contrast characteristics. Fit bounded parameters in our renderer, preserve scene structure, and expose the result as a suggestion. Keep lighting and composition mismatch visible as limitations.
- Fixture: A reference shot with dramatic directional lighting and a user source recorded under flat overhead light.
- Oracle: The tool proposes a bounded grade but does not claim to recreate the missing lighting geometry.
- Mutant that must fail: Use unconstrained neural stylization and call altered faces faithful source footage.

Machine-readable fixture: [P142_IMPLEMENT_CONSTRAINED_REFERENCE_MATCHING.json](P142_IMPLEMENT_CONSTRAINED_REFERENCE_MATCHING.json).

`scripts/gates/p142_implement_constrained_reference_matching.py` fits exposure, contrast, and saturation only. Declared bounds are exposure [-2, 2], contrast [0.5, 1.5], and saturation [0, 2]. Face landmark drift above 0.02 is rejected. A matcher may suggest those numeric parameters only. If `output_sha256` differs from `source_sha256` and the result is labelled source footage, the result is rejected. Neural stylization (`method` `stylize`) that changes pixels is rejected as faithful source footage. A suggestion that keeps the source hash and stays in bounds is recorded as a parameter suggestion, not a new source. Lighting and composition mismatch stay visible; the grade does not recreate lighting geometry. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p142*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P142-01 through TC-P142-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
