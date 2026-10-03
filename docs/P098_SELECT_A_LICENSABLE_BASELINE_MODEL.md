# P098 — Select a licensable baseline model

Active phase: **P098**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Model selection record and licence manifest". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Model selection record and licence manifest

- Goal: Choose the smallest credible model that can establish the pipeline without blocking future commercial use.
- Method: Review the exact weight licence, code licence, export dependencies, and redistribution conditions. Record model hashes and training-domain limitations. Evaluate a small baseline against owned test clips before adding larger alternatives.
- Fixture: Two similarly named model variants with different licences and substantially different memory requirements.
- Oracle: The package includes only approved weights and reports the selected variant exactly.
- Mutant that must fail: Assume all variants inherit the most permissive licence in the repository.

Machine-readable fixture: [P098_SELECT_A_LICENSABLE_BASELINE_MODEL.json](P098_SELECT_A_LICENSABLE_BASELINE_MODEL.json).

`scripts/gates/p098_select_a_licensable_baseline_model.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p098*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P098-01 through TC-P098-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
