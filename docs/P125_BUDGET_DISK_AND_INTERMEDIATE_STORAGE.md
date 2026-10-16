# P125 — Budget disk and intermediate storage

Active phase: **P125**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Storage planner and low-space continuation policy". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Storage planner and low-space continuation policy

- Goal: Prevent high-quality development from filling storage and destroying recoverability.
- Method: Estimate source, proxy, temporary, finalization, and publication requirements separately. Use conservative reserves and measured growth, not a fixed generic percentage. Allow explicit cleanup of reproducible intermediates while protecting originals and sole retained outputs.
- Fixture: A long RAW source whose planned ten-bit export requires temporary duplication during publication.
- Oracle: The job declines or pauses safely before exhausting reserved space and explains which data can be removed safely.
- Mutant that must fail: Budget only the final output size and ignore temporary files.

Machine-readable fixture: [P125_BUDGET_DISK_AND_INTERMEDIATE_STORAGE.json](P125_BUDGET_DISK_AND_INTERMEDIATE_STORAGE.json).

Reserve bytes = source_bytes + intermediate_estimate_bytes + safety_bytes.
The same relation is `reserve = source_bytes + intermediate_estimate_bytes + safety_bytes`.
Headroom bytes = free_bytes - reserve. `safety_bytes` is passed explicitly and
is not a percentage of free space. Source, proxy, temporary, finalization, and
publication are estimated separately; `intermediate_estimate_bytes` is the
measured intermediate total.

The numeric fixture is a long RAW source of 8000000000 bytes, 100 frames at
40000000 bytes each (implied intermediate 4000000000, the ten-bit temporary
duplication), an intermediate estimate of 4000000000, and an explicit safety
reserve of 250000000. Reserve is 12250000000. Free space is 20000000000, so
headroom is 7750000000 and start is allowed. If free_bytes is below that
reserve, start_allowed must be false; start_allowed true is rejected and
headroom stays negative only because start is refused. delete_source is always
rejected. An intermediate estimate of 0 while frame_count * bytes_per_frame is
positive is rejected. Reproducible intermediates may be removed. Source
originals and sole retained outputs stay protected.

`scripts/gates/p125_budget_disk_and_intermediate_storage.py` rejects `applyMutant`,
a start below the reserve, deleting the source, and a budget that ignores
intermediates. The evidence id stays in `preservedResults`. The decision is
never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p125*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P125-01 through TC-P125-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
