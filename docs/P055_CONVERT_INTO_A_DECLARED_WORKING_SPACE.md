# P055 — convert into a declared working space

Active phase: **P055**. Entry gate: **P054**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for a declared working-space conversion. It does
**not** measure a physical Galaxy S23. A green host run is not that measurement
and is not physical S23 qualification.

## Deliverable

Working-image descriptor and color conversion tests.

Machine-readable fixture:
[P055_CONVERT_INTO_A_DECLARED_WORKING_SPACE.json](P055_CONVERT_INTO_A_DECLARED_WORKING_SPACE.json)
(`schemaVersion` 1, `phase` `P055`, `mapId` `s23-declared-working-space-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture states order `camera-transform`, then `exposure-scale`, then
`working-store`. Units are `scene-linear`. The white point is the declared
assumption `D65`, not a measurement. Precision is `float64`. The documented
storage boundary is `-8..16`, wider than display `0..1`. Diffuse white is `1`.

Source `saturated-highlight` is camera RGB `2, 0.1, 0.1`. The camera matrix
and exposure scale `2` produce working RGB `4, -1.8, 0.2`. Channel G is
negative. Channel R is above diffuse white. The independent reference
`independent-vector` stores that same triple. It is not an eight-bit code.

`scripts/gates/p055_convert_into_a_declared_working_space.py` encodes the
phase method, fixture, oracle, and mutant:

- `assess` on the declared path decides `working_retained`. `preservedResults`
  keep the source, the unclipped working vector, the negative channel, the
  highlight, the white point, the units, and the order. `working_retained` is
  not `qualified` and not `allowed`.
- The mutant path `eight-bit-display` inserts an eight-bit display bitmap
  between the camera transform and the working image. It decides `rejected`
  with `eight-bit-display-bitmap` and `display-gamut-clip`. The bitmap is
  `1, 0, 0.2`. The unclipped working vector `4, -1.8, 0.2` stays in the
  inventory. A test fails if that mutant is what the declared path returns.
- A singular or nonfinite transform is `rejected`. A reference mismatch is
  `rejected` and still keeps the computed vector. Values outside the
  documented storage boundary are `bounded`, not display-clipped.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p055*.py' -v
```

The phase test loads the fixture, checks that the negative channel and the
highlight above diffuse white survive, and checks that the eight-bit display
bitmap is rejected. Case modules TC-P055-01 through TC-P055-08 are separate
files. This phase module does not call them. The command above runs their
host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- Preserving a signed host vector does not prove fixed cadence, sensor-derived
  Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- The matrix, the exposure scale, and the D65 label are declared assumptions.
  They are not a measured camera-to-working profile from a physical capture.
- An eight-bit display bitmap is not a working image. Display-gamut clipping
  is not evidence that highlights or negative channels were retained.
- No Kotlin, Gradle, or workflow sources were changed.
