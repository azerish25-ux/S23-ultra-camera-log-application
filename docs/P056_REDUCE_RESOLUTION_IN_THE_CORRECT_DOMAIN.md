# P056 — reduce resolution in the correct domain

Active phase: **P056**. Entry gate: **P055**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for scene-linear resolution reduction. It does **not**
measure a physical Galaxy S23. A green host run is not that measurement and is
not physical S23 qualification.

## Deliverable

Resampling module and geometry provenance tests.

Machine-readable fixture:
[P056_REDUCE_RESOLUTION_IN_THE_CORRECT_DOMAIN.json](P056_REDUCE_RESOLUTION_IN_THE_CORRECT_DOMAIN.json)
(`schemaVersion` 1, `phase` `P056`, `mapId` `s23-linear-domain-reduction-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is a 4×4 scene-linear frame reduced to 2×2 by a box prefilter.
The crop is the full frame. The actual area reduction ratio is 1/4
(axis ratios 1/2 and 1/2). Alternating bins average to 0.52 and 0.5 in linear
light. Constant bins stay 0.04 and 1. A separable cubic tap `[1, 6, 1] / 8`
on that box grid is a different resample
(`0.4728125`, `0.5496875`, `0.2046875`, `0.8328125`) and is not reported as
the box result. Tiles of size 2 match the untiled box result. The same tile
size does not match the full-frame cubic result, because cubic support crosses
the tile seam.

`host-logc-toy` is `x / (x + 1)` on non-negative linear values, decoded by
`y / (1 - y)`. It is a host compressive code so the average of encoded samples
can be compared with the linear mean. It is not ARRI LogC. The first bin's
encoded average decodes to 7/19, not 0.52.

`scripts/gates/p056_reduce_resolution_in_the_correct_domain.py` encodes the
phase method, fixture, oracle, and mutant:

- `assess` keeps every source pixel, the box means, the cubic resample, the
  encoded-value averages, the declared reference, and the reduction ratio in
  `preservedResults`. The fixture decision is `linear-reduced`. That label is
  not `qualified` and not `allowed`.
- The mutant `average_domain="logc"` is `rejected` with
  `logc-average-labeled-scene-linear`. A constant field whose decoded code
  average equals the linear mean is still rejected. A test fails if that
  mutant is implemented as `scene-linear`, `linear-reduced`, `qualified`, or
  `allowed`.
- An axis increase is `mislabeled-upscale`. Equal output area is
  `not-a-reduction`. A declared reference that disagrees is
  `reference-mismatch`. Crop geometry stays in provenance when the window is
  not the full frame.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p056*.py' -v
```

The phase test loads the fixture, checks that the box output matches an
independent bin mean and the declared reference, records reduction ratio 1/4,
and checks that averaging host-logc-toy codes is rejected. Case modules
TC-P056-01 through TC-P056-08 are separate files. This phase module does not
call them. The command above runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- `linear-reduced` does not certify a camera master, fixed cadence, ten-bit
  fidelity, film-stock fidelity, or cinema-camera equivalence.
- `host-logc-toy` is not sensor-derived Log and is not ARRI LogC or any
  camera log encoding.
- The box and cubic numbers are not a measured resample from a physical
  capture, and they are not an upscaler.
- No Kotlin, Gradle, or workflow sources were changed.
