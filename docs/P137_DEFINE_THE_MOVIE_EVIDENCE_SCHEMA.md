# P137 — Define the movie evidence schema

Active phase: **P137**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Movie-claim schema and evidence-state tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Movie-claim schema and evidence-state tests

- Goal: Represent production facts, reconstruction choices, and unknowns as different data types.
- Method: Store movie, scene family, acquisition format, stock, camera and lens facts, processing notes, release reference, citations, confidence, and our recipe parameters. Every documented or contradicted claim needs a source; unknown values remain null rather than guessed.
- Fixture: A film with documented stock choices but no verified lens information for the selected scene.
- Oracle: The recipe can use a clearly reconstructed virtual lens while retaining the production lens field as unknown.
- Mutant that must fail: Fill missing lens fields with plausible cinema equipment and mark them documented.

Machine-readable fixture: [P137_DEFINE_THE_MOVIE_EVIDENCE_SCHEMA.json](P137_DEFINE_THE_MOVIE_EVIDENCE_SCHEMA.json).

`scripts/gates/p137_define_the_movie_evidence_schema.py` stores each field as one of three states: `fact`, `reconstruction`, or `unknown`. A fact requires a `source_id`. An unknown value is null. Counts of each state are retained. The Northwater fixture keeps the production lens unknown and the virtual lens as a reconstruction, with the stock left as a sourced fact. Filling that missing lens with a guessed name marked `documented` or `fact` is rejected, and the lens stays unknown. A reconstruction is not relabelled fact. A record that mixes those states on one claim is rejected. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p137*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P137-01 through TC-P137-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
