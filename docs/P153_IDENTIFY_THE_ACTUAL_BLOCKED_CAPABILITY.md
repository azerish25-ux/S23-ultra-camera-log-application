# P153 — Identify the actual blocked capability

Active phase: **P153**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Blocked-capability hypothesis and evidence dossier". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Blocked-capability hypothesis and evidence dossier

- Goal: State a concrete research question before proposing firmware work.
- Method: Use current public diagnostics and failed qualified app experiments to locate the bottleneck: sensor stream, HAL exposure, codec interface, synchronization, or app performance. Specify the desired observation and an alternative application-level path. Avoid vague goals such as unlock everything.
- Fixture: A RAW route limited by measured disk throughput rather than a denied camera mode.
- Oracle: The research plan addresses storage and buffering before proposing a firmware modification.
- Mutant that must fail: Attribute every low frame rate to Samsung restrictions without measurements.

Machine-readable fixture: [P153_IDENTIFY_THE_ACTUAL_BLOCKED_CAPABILITY.json](P153_IDENTIFY_THE_ACTUAL_BLOCKED_CAPABILITY.json).

`scripts/gates/p153_identify_the_actual_blocked_capability.py` records a hypothesis only when it names `capability`, `measurement_id` or null, `observed_fps`, `advertised_fps`, and `blamed` (`app`, `codec`, `thermal`, `firmware`, or `unknown`). Blaming firmware or Samsung with `measurement_id` null is rejected. A concrete question is recorded only when the capability and the missing measurement are both named. Low fps alone is not proof of a restriction. An unmeasured fps drop cannot prove a firmware restriction, a Samsung restriction, or any vendor block. The RAW fixture is limited by measured disk throughput, so the plan addresses storage and buffering, and an alternative application path, before any firmware modification. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p153*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P153-01 through TC-P153-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
