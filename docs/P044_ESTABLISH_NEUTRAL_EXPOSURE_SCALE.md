# P044 — establish neutral exposure scale

Active phase: **P044**. Entry gate: **P043**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for a neutral-reference measurement and a guarded
scale estimator. It does **not** measure a physical Galaxy S23. A green host
run is not that measurement and is not physical S23 qualification.

## Deliverable

Neutral-reference measurement and guarded scale estimator.

Machine-readable fixture:
[P044_ESTABLISH_NEUTRAL_EXPOSURE_SCALE.json](P044_ESTABLISH_NEUTRAL_EXPOSURE_SCALE.json)
(`schemaVersion` 1, `phase` `P044`, `mapId` `s23-neutral-exposure-scale-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture keeps source frame `frame-neutral-044`. Patch `white-object` at
ROI `120,40,80,80` is a bright white signal `9100` misidentified as
eighteen-percent grey. Patch `grey-specular` at ROI `400,220,60,60` is partly
clipped (`clippedFraction` 18) by a specular reflection and is textured. The
whole-frame mean luminance is `7200`. Middle grey on this fixture is code
`1800`. Those two numbers are not the same, and the mean is not a neutral
target.

`scripts/gates/p044_establish_neutral_exposure_scale.py` encodes the phase
method, fixture, oracle, and mutant:

- `assess` inspects each user-confirmed patch for clipping, texture, signal
  level, and color neutrality. `preservedResults` keep the frame id, both ROI
  coordinates, both patch tokens, the whole-frame mean, and the middle-grey
  code. Chromatic fitting stays `chromatic-fit:withheld`.
- The fixture decision is `withheld`, never `qualified` or `allowed`. No
  `exposure-scale` token is emitted. `rejectedClaims` name the misidentified
  bright white object, the partial specular clip, and
  `whole-frame-mean-not-middle-grey`. Reasons request valid evidence and
  record uncertainty instead of a confidently measured scale.
- The mutant sole test `mean-luminance-middle-grey` is `rejected`. Assuming
  the mean image luminance always corresponds to middle grey does not invent
  a scale. A test fails if that mutant is implemented as a pass.
- A later valid patch may record an explicitly provisional ratio. That ratio
  is still not a measured profile and is not derived from the frame mean.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p044*.py' -v
```

The phase test loads the fixture, checks that the bright white object and the
partly clipped grey patch do not produce a measured scale, and checks that
mean luminance is not middle grey. Case modules TC-P044-01 through TC-P044-08
are separate files. This phase module does not call them. The command above
runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- Whole-frame mean luminance is not eighteen-percent grey and is not an
  exposure scale.
- A provisional ratio on a valid patch is not a confidently measured profile,
  not sensor-derived Log, and not ten-bit or film-stock fidelity.
- The gate does not claim cinema-camera equivalence or fixed cadence.
- No Kotlin, Gradle, or workflow sources were changed.
