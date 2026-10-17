# P145 — Build the layered automated test system

Active phase: **P145**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Layered CI plan and machine-readable evidence aggregation". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Layered CI plan and machine-readable evidence aggregation

- Goal: Separate host arithmetic, JVM policies, Android integration, GPU parity, and physical acceptance.
- Method: Run fast deterministic contracts on every change, then focused integration suites and scheduled device experiments. Preserve failing evidence and classify unavailable hardware explicitly. Tests must call production interfaces or declared independent references, not duplicate trivial implementations.
- Fixture: A green host suite alongside an unavailable physical ten-bit codec test and a failing GPU color test.
- Oracle: The report keeps the GPU failure and unavailable device gate visible and does not declare the release fully qualified.
- Mutant that must fail: Count skipped hardware tests as passing tests in the release summary.

Machine-readable fixture: [P145_BUILD_THE_LAYERED_AUTOMATED_TEST_SYSTEM.json](P145_BUILD_THE_LAYERED_AUTOMATED_TEST_SYSTEM.json).

`scripts/gates/p145_build_the_layered_automated_test_system.py` separates the layers `host`, `jvm`, `android`, `gpu`, and `physical`. Each layer keeps its own `passed`, `failed`, and `skipped` counts. Skipped tests are counted only in `skipped`. `totalPassed` and the honest `releasePassed` equal the sum of per-layer `passed` and do not include skipped. Adding skipped into a layer's `passed` count, or a `releasePassed` that includes skipped, is rejected. The release summary lists each layer separately. A missing physical layer is `not-run` with `passed` 0, not passed. The GPU color failure and the unavailable physical ten-bit codec stay visible. The decision is `recorded` or `rejected`, never `qualified` or `allowed`. The evidence id stays in `preservedResults`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p145*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P145-01 through TC-P145-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
