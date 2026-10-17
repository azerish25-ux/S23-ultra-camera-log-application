# P157 — Design instrumented low-level experiments

Active phase: **P157**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Instrumented experimental protocol and observation schema". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Instrumented experimental protocol and observation schema

- Goal: Make any authorized low-level change minimal, observable, and reversible where technically possible.
- Method: Change one hypothesized constraint at a time, preserve the baseline, record checksums and logs, and define failure triggers before execution. Do not disable thermal safeguards or falsify capability metadata to make unsupported modes appear available.
- Fixture: A modification that changes advertised stream metadata but produces no valid additional sensor frames.
- Oracle: The experiment fails its actual-delivery hypothesis despite the expanded menu.
- Mutant that must fail: Call an advertised mode unlocked without capturing and validating its output.

Machine-readable fixture: [P157_DESIGN_INSTRUMENTED_LOW_LEVEL_EXPERIMENTS.json](P157_DESIGN_INSTRUMENTED_LOW_LEVEL_EXPERIMENTS.json).

`scripts/gates/p157_design_instrumented_low_level_experiments.py` records an instrumented protocol only as a design, not as a completed device experiment. An experiment has a change description, a reversible bool, observation fields, and a `captured_output` bool. Calling a mode unlocked (`unlocked_claim` true) without `captured_output` is rejected. A change that is not reversible must list a recovery step or be rejected. Observations must include distinct before and after identifiers. The experiment checksum must match those fields. One hypothesized constraint is changed at a time, the baseline stays preserved, and failure triggers are defined before execution. Disabling thermal safeguards or falsifying capability metadata is rejected. Evidence stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p157*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P157-01 through TC-P157-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
