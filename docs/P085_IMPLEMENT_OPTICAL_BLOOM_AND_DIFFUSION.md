# P085 — Implement optical bloom and diffusion

Active phase: **P085**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Optical diffusion module and energy-response tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Optical diffusion module and energy-response tests

- Goal: Treat lens or filter scatter as a distinct, optional image-formation component.
- Method: Use normalized kernels or an explicitly documented flare model in the relevant exposure domain. Control veiling glare, local spread, and highlight behavior independently from emulsion effects. Validate the interaction with clipping and virtual bokeh.
- Fixture: A point light near a dark face, a broad soft source, and a highlight already clipped in the source.
- Oracle: The effect remains finite and cannot claim to restore the clipped source; broad sources do not receive implausible identical halos.
- Mutant that must fail: Blur a thresholded eight-bit image and add it without any energy or clipping policy.

Machine-readable fixture: [P085_IMPLEMENT_OPTICAL_BLOOM_AND_DIFFUSION.json](P085_IMPLEMENT_OPTICAL_BLOOM_AND_DIFFUSION.json).

`scripts/gates/p085_implement_optical_bloom_and_diffusion.py` rejects `applyMutant` and a reversed sample wedge. The evidence
id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p085*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P085-01 through TC-P085-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
