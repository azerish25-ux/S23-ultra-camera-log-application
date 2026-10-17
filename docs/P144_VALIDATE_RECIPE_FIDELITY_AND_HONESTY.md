# P144 — Validate recipe fidelity and honesty

Active phase: **P144**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Recipe evaluation report and catalogue quality policy". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Recipe evaluation report and catalogue quality policy

- Goal: Evaluate whether recipes are coherent and enjoyable without overstating historical or physical accuracy.
- Method: Use matched owned sources, blind preference tests, parameter ablations, and expert review where possible. Score evidence completeness separately from appearance preference. A popular recipe may remain reconstructed; a well-sourced recipe may need artistic refinement.
- Fixture: One visually preferred recipe with uncertain production facts and another fully sourced but less preferred interpretation.
- Oracle: The app reports these different qualities without promoting preference into factual certainty.
- Mutant that must fail: Use user star ratings as evidence that a stock identification is correct.

Machine-readable fixture: [P144_VALIDATE_RECIPE_FIDELITY_AND_HONESTY.json](P144_VALIDATE_RECIPE_FIDELITY_AND_HONESTY.json).

`scripts/gates/p144_validate_recipe_fidelity_and_honesty.py` separates coherence (0..1), enjoyment (0..1 or null), and identification. Identification is correct only with a `source_id` and `evidence_kind` `"source"`. Using `star_rating` as identification evidence is rejected. High enjoyment does not flip identification to correct. A recipe can be recorded as enjoyable and unidentified. Historical accuracy is not claimed without a source. The preferred fixture stays reconstructed; the less preferred fixture stays identified only by its owned source. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

Catalogue policy: evidence completeness is scored apart from appearance preference, a popular recipe may remain reconstructed, a well-sourced recipe may need artistic refinement, and a star rating does not identify stock.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p144*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P144-01 through TC-P144-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
- A star rating cannot prove a stock or lens identification, historical accuracy, or that identification is correct.
