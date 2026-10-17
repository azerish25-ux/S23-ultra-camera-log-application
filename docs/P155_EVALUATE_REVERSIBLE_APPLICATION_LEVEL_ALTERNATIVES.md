# P155 — Evaluate reversible application-level alternatives

Active phase: **P155**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Alternative-path experiments and comparative decision". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement. physical S23 not run.

## Deliverable

Alternative-path experiments and comparative decision

- Goal: Exhaust useful normal-app approaches before escalating risk.
- Method: Compare alternate stream combinations, smaller source sizes, different codec interfaces, deferred development, CPU-GPU scheduling, and retained RAW workflows. Measure the information and quality tradeoffs. Keep each alternative honestly labelled by source lineage.
- Fixture: A surface-only ten-bit encoder that could support a qualified GPU route even though the P010 Image developer is unavailable.
- Oracle: The plan explores that interface before declaring the sensor-to-Log goal impossible.
- Mutant that must fail: Treat failure of one codec input interface as proof that every ten-bit path is unavailable.

Machine-readable fixture: [P155_EVALUATE_REVERSIBLE_APPLICATION_LEVEL_ALTERNATIVES.json](P155_EVALUATE_REVERSIBLE_APPLICATION_LEVEL_ALTERNATIVES.json).

`scripts/gates/p155_evaluate_reversible_application_level_alternatives.py` compares alternatives. Each alternative is `{name, tried, result}` and `result` is `available`, `unavailable`, or `untested`. A path has been tried only when `tried` is true and `result` is `available` or `unavailable`. A path is explicitly left untested only when `tried` is false and `result` is `untested`. Failure of one codec interface does not mark every other ten-bit path unavailable; each path keeps its own result, source lineage, and information or quality tradeoff. Untested paths stay unknown. If any alternative is untested, a conclusion that all ten-bit paths are unavailable is rejected. A comparative decision is recorded only when every listed path has been tried or explicitly left untested and the conclusion matches those results. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p155*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- physical S23 not run.
- It does not certify sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P155-01 through TC-P155-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
