# P051 — row-streamed reference demosaic

Active phase: **P051**. Entry gate: **P050**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for a bounded-memory bilinear demosaic. It does
**not** measure a physical Galaxy S23. A green host run is not that measurement
and is not physical S23 qualification.

## Deliverable

CPU reference demosaic and exact synthetic goldens.

Machine-readable fixture:
[P051_BUILD_THE_ROW_STREAMED_REFERENCE_DEMOSAIC.json](P051_BUILD_THE_ROW_STREAMED_REFERENCE_DEMOSAIC.json)
(`schemaVersion` 1, `phase` `P051`, `mapId`
`s23-row-streamed-bilinear-demosaic-fixture`, implementation base
`d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is an authored mosaic, not a sensor dump. It holds a uniform field
with padded source rows, a Bayer impulse near each edge, a vertical edge, a
red checkerboard, an odd crop, and a signed constant field. Output samples are
exact rationals (`7/2`, not a rounded float).

Border policy: average in-bounds same-channel neighbors at Chebyshev distance
1, and copy a known site. A missing row is omitted. It is not replicated, not
replaced by zero, and not read from a stale slot. Padding at or beyond the
owned width is not a sample. Worked RGGB impulse of 12 at `(0, 1)`: pixel
`(0, 0)` green is `(12 + 0) / 2 = 6`. Impulse 12 at `(3, 0)`: pixel `(3, 1)`
green is `12 / 3 = 4`. Feeding a stale zero in as the missing row below makes
that `12 / 4 = 3`.

White balance is a separate per-channel linear stage. The interpolator does
not take gains. Placement before or after interpolation agrees. Scaling a
neighbor by the center site's gain is not the reference.

Row window: three owned slots. Output row `y` may read only source rows in
`[max(0, y-1), min(height-1, y+1)]`. A released slot is stale. Each retained
row is a copy of the owned samples.

`scripts/gates/p051_build_the_row_streamed_reference_demosaic.py` encodes the
phase method, fixture, oracle, and mutant:

- `demosaic` / `stream_demosaic` are the honest reader. Decision from `assess`
  on the fixture is `matched`, never `qualified` or `allowed`.
- `demosaic_stale_mutant` and `assess(..., read_stale=True)` reject the mutant
  that reads a missing neighboring row from a stale buffer slot. The scene
  inventory stays in `preservedResults`.
- `apply_white_balance` is outside interpolation. `demosaic_mixed_gains` is not
  the reference.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p051*.py' -v
```

The phase test loads the fixture, checks the hand-derived borders above, checks
that padding and stale slots are not read, and checks that implementing the
mutant would disagree with those borders. Case modules TC-P051-01 through
TC-P051-08 are separate files. This phase module does not call them. The
command above runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- A matched bilinear golden is not a native kernel, a GPU kernel, sensor-derived
  Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- White-balance gains in the host test are not a measured camera neutral.
- No fixed cadence is claimed. Exact rationals are not a claim of ten-bit
  capture fidelity.
- No Kotlin, Gradle, or workflow sources were changed.
