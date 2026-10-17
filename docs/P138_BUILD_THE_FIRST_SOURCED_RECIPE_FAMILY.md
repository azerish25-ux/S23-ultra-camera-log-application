# P138 — Build the first sourced recipe family

Active phase: **P138**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Initial recipe family with source-to-field traceability". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Initial recipe family with source-to-field traceability

- Goal: Demonstrate the database with a small, well-supported set rather than hundreds of names.
- Method: Use primary production accounts where available and separate daylight, low-light, monochrome, and format variants. Record the exact scope of each source. Do not extend a statement about a whole production into an unsupported claim about every shot.
- Fixture: A production account documenting several stocks used under different shooting conditions.
- Oracle: The database creates separate supported variants and clearly marks any scene-specific reconstruction.
- Mutant that must fail: Assign one stock and one lens to every scene because the film title matches.

Machine-readable fixture: [P138_BUILD_THE_FIRST_SOURCED_RECIPE_FAMILY.json](P138_BUILD_THE_FIRST_SOURCED_RECIPE_FAMILY.json).

`scripts/gates/p138_build_the_first_sourced_recipe_family.py` records a recipe family only when each non-null stock or lens has a trace `{field, source_id}` with a non-empty `source_id`. Assigning stock and lens because the title matches, with empty traces, is rejected. A family larger than the declared maximum (12 when the document sets `max_entries`) without sources is rejected. Unknown fields stay null rather than invented. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p138*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P138-01 through TC-P138-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
