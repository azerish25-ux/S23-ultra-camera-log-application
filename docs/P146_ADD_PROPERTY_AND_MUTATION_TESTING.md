# P146 — Add property and mutation testing

Active phase: **P146**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Property generators and critical mutation catalogue". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Property generators and critical mutation catalogue

- Goal: Prove that tests can detect plausible defects rather than merely execute lines.
- Method: Generate valid and invalid numeric domains, temporal event sequences, geometry combinations, and malformed records. Introduce selected mutants such as range confusion, timestamp reuse, CFA swaps, and missing hash checks. Require critical mutants to be killed by the intended tests.
- Fixture: A mutation replacing exact timestamp pairing with nearest-neighbor matching.
- Oracle: The metadata association test fails for the deliberately close-but-wrong timestamp fixture.
- Mutant that must fail: Run only happy-path examples with conveniently identical metadata.

Machine-readable fixture: [P146_ADD_PROPERTY_AND_MUTATION_TESTING.json](P146_ADD_PROPERTY_AND_MUTATION_TESTING.json).

`scripts/gates/p146_add_property_and_mutation_testing.py` records a mutation catalogue only when each mutant has `input`, `expected_detection` true, and a `detected` bool, and at least one field of `input` differs from `original` (or a declared `changedField` when `original` is absent). A catalogue that is only happy-path examples, with no mutant that has a changed field, is rejected. A mutant that should be detected (`expected_detection` true) but `detected` is false survives and is rejected. The fixture mutant replaces exact timestamp pairing with nearest-neighbor matching on a close-but-wrong timestamp; that mutant must be killed, because the metadata association test fails for it. For a list of numeric samples, shuffling order must not change the commutative sum. If that property fails, the implementation claim is rejected. Identical metadata on every example labelled as a property suite is rejected. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p146*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P146-01 through TC-P146-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
