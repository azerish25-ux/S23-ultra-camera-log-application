# P087 — Add aging and mechanical imperfections as optional layers

Active phase: **P087**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Optional aging module and clean-default tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Optional aging module and clean-default tests

- Goal: Support expressive damaged-film looks without making damage synonymous with cinematic quality.
- Method: Keep dust, scratches, gate weave, flicker, burns, and frame instability in a separately named effects group. Give each deterministic timing and geometry controls. Defaults for clean 35mm and large-format looks should not add arbitrary damage.
- Fixture: A clean large-format preset and an explicitly aged Super 8 preset rendered from the same source.
- Oracle: The clean preset contains no unrequested scratches or gate jitter, and the aged effects are reproducible and independently removable.
- Mutant that must fail: Enable strong scratches in every preset to make the film simulation more obvious.

Machine-readable fixture: [P087_ADD_AGING_AND_MECHANICAL_IMPERFECTIONS_AS_OPTION.json](P087_ADD_AGING_AND_MECHANICAL_IMPERFECTIONS_AS_OPTION.json).

`scripts/gates/p087_add_aging_and_mechanical_imperfections_as_option.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p087*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P087-01 through TC-P087-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
