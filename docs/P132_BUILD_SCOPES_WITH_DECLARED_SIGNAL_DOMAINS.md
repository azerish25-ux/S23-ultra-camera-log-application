# P132 — Build scopes with declared signal domains

Active phase: **P132**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host reference for "Scope domain model and monitoring correctness tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Scope domain model and monitoring correctness tests

- Goal: Make waveform, histogram, clipping, and false color informative rather than misleading.
- Method: Label whether a scope measures source, working image, encoded Log, or display preview. Record sampling resolution and freshness. Preview-only RGB8 aids cannot certify sensor clipping or ten-bit precision. Keep scope computation off critical capture ownership.
- Fixture: A clipped display preview of an unclipped high-range source and a stale waveform after inference load spikes.
- Oracle: The scope identifies its domain and stale status rather than falsely declaring source clipping from the preview.
- Mutant that must fail: Label every preview histogram sensor exposure regardless of its input.

Machine-readable fixture: [P132_BUILD_SCOPES_WITH_DECLARED_SIGNAL_DOMAINS.json](P132_BUILD_SCOPES_WITH_DECLARED_SIGNAL_DOMAINS.json).

`scripts/gates/p132_build_scopes_with_declared_signal_domains.py` gives every scope a kind (`histogram`, `waveform`, `clipping`, `false_color`) and a domain in `{display_sdr, hlg_signal, sensor_code, unknown}`. A missing domain is not a domain. A histogram whose samples are display RGB must not be labelled `sensor_exposure`. A `sensor_exposure` label with domain `unknown` or missing is rejected. Relabeling a display histogram (`display_sdr`, or a prior display label) as `sensor_exposure` is rejected. False color must name its input domain as `display_sdr`, `hlg_signal`, or `sensor_code`. Clipping counts are the number of samples strictly above a declared threshold and are retained in `preservedResults`, including when the decision is rejected. The fixture preview clipping count is 3 and the high-range source clipping count is 0. The stale waveform stays `display_sdr` and stale. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p132*.py' -v
```

## Non-claims

- This is an authored host reference, not a device probe and not a physical S23 measurement.
- It does not certify sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P132-01 through TC-P132-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
