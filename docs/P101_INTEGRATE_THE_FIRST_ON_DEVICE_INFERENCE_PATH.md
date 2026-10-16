# P101 — Integrate the first on-device inference path

Active phase: **P101**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host reference for "Offline inference integration and no-network tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Offline inference integration and no-network tests

- Goal: Run the approved model locally with bounded ownership and an explicit fallback policy.
- Method: Benchmark the selected runtime and delegate under actual app load. Separate model download or installation from inference. The app must work offline after assets are present, and failure must leave capture usable without virtual blur.
- Fixture: Airplane mode, a missing model asset, and a delegate initialization failure during preview.
- Oracle: The UI reports the issue, avoids network-dependent generation, and preserves ordinary recording.
- Mutant that must fail: Block camera startup until a cloud inference service responds.

Machine-readable fixture: [P101_INTEGRATE_THE_FIRST_ON_DEVICE_INFERENCE_PATH.json](P101_INTEGRATE_THE_FIRST_ON_DEVICE_INFERENCE_PATH.json).

`scripts/gates/p101_integrate_the_first_on_device_inference_path.py` computes model identity as SHA-256 of the content plus precision and runtime version, restores letterbox corner markers from recorded scale, pad, and channel order, and rejects a cloud startup block. A missing local asset reports the missing capability and leaves capture usable. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p101*.py' -v
```

## Non-claims

- This is an authored host reference, not a device probe and not a physical S23 measurement.
- It is not physical S23, not sensor-derived Log, not ten-bit fidelity, not film-stock fidelity, and not cinema-camera equivalence.
- TC-P101-01 through TC-P101-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
