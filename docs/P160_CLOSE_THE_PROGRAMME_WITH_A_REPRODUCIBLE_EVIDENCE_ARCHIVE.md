# P160 — Close the programme with a reproducible evidence archive

Active phase: **P160**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Final research archive, maintenance guide, and evidence-bound roadmap". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Final research archive, maintenance guide, and evidence-bound roadmap

- Goal: Leave a maintainable application and an honest record of what the research established.
- Method: Archive source revisions, approved profiles, model identities, fixture rights, test commands, physical reports, known limitations, and deferred hypotheses. Preserve failed experiments that explain design decisions. The final claim set must be reproducible from evidence without relying on the original developer’s memory.
- Fixture: A new maintainer rebuilding the app and reproducing one capture, one film render, and one virtual-lens evaluation.
- Oracle: The archive provides enough information to reproduce qualified behaviour and clearly identifies unavailable physical prerequisites.
- Mutant that must fail: Delete unsuccessful experiments and publish only attractive final renders.

Machine-readable fixture: [P160_CLOSE_THE_PROGRAMME_WITH_A_REPRODUCIBLE_EVIDENCE_ARCHIVE.json](P160_CLOSE_THE_PROGRAMME_WITH_A_REPRODUCIBLE_EVIDENCE_ARCHIVE.json).

`scripts/gates/p160_close_the_programme_with_a_reproducible_evidence_archive.py` records an archive only when every record has `id`, `outcome` (`passed`, `failed`, or `not_run`), and `retained`. Deleting a failed experiment (`retained` false for outcome `failed`) is rejected. The archive must include failed and `not_run` records, not only passes. The maintenance note must state that physical S23, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not established. Publishing only attractive renders (`only_passes` true) is rejected. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p160*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- Those limits are not established.
- TC-P160-01 through TC-P160-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
