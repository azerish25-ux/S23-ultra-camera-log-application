# P046 — implement illuminant adaptation carefully

Active phase: **P046**. Entry gate: **P045**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for illuminant handling and adaptation test vectors.
It does **not** measure a physical Galaxy S23. A green host run is not that
measurement and is not physical S23 qualification.

## Deliverable

Illuminant handling decision and adaptation test vectors.

Machine-readable fixture:
[P046_IMPLEMENT_ILLUMINANT_ADAPTATION_CAREFULLY.json](P046_IMPLEMENT_ILLUMINANT_ADAPTATION_CAREFULLY.json)
(`schemaVersion` 1, `phase` `P046`, `mapId` `s23-illuminant-adaptation-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture scene is mixed: `daylight` and `narrow-band-colored-led`, with one
global neutral measurement `1200,1000,800` on patch `daylight-gray`.

Endpoint meanings, kept distinct:

- `daylight` is a **reference-white** matrix under `row-camera-to-xyz`. Its
  neutral `1000,1000,1000` is the reference white vector, not a camera
  spectral-sensitivity model. The matrix condition number is `7/3`. The
  neutral response is `3000,3000,3000`.
- `narrow-band-led` is a **spectral-sensitivity** matrix under the same
  convention. Its neutral `400,1000,200` is the sensor neutral for that model,
  not a reference-white adaptation. The condition number is `5/3`. The
  neutral response is `2000,3000,800`.

The declared adaptation is only `von-kries-reference-white` with gains
`5/6,1/1,5/4` from the daylight neutral toward the global measurement. The
spectral-sensitivity matrix is labeled unchanged. Infinity-norm conditioning
uses limit `20/1`. Interpolation is not requested on the fixture. A checked
interpolation, when it is used at all, is sampled at `0/1`, `1/4`, `1/2`,
`3/4`, and `1/1` and is never substituted for the declared gains. Mixed
illumination stays labeled: one global neutral does not solve arbitrary
spectra.

`scripts/gates/p046_implement_illuminant_adaptation_carefully.py` encodes the
phase method, fixture, oracle, and mutant:

- `assess` returns `adaptation_limited` for the fixture, never `qualified` or
  `allowed`. `rejectedClaims` are `universal-matching` and
  `spectral-sensitivity-rewrite`. `preservedResults` keep the scene, the
  neutral, both endpoint tokens, the von Kries gains, and the unchanged
  spectral-sensitivity id.
- The mutant sole test `unchecked-element-interpolation` is `rejected`. The
  element-wise midpoint of the two endpoint matrices is a rejected claim
  (`element-lerp:1/2:7/2,1/2,0/1,0/1,5/2,1/2,1/2,0/1,3/1`) and is not installed
  as the adaptation. A test fails if that mutant is implemented as a pass.
- An interpolation request that skips convention or neutral-response checks is
  rejected on the declared path as well. Pairing the spectral-sensitivity
  endpoint into the white-adaptation domain is not valid.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p046*.py' -v
```

The phase test loads the fixture, checks that the declared von Kries gains stay
distinct from the spectral-sensitivity matrix, and checks that unchecked
element interpolation is rejected. Case modules TC-P046-01 through TC-P046-08
are separate files. This phase module does not call them. The command above
runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- Reference-white adaptation is not a change to a camera spectral-sensitivity
  model and is not universal matching under mixed daylight and narrow-band LEDs.
- A finite matrix, a finite determinant, or an identity fallback is not a
  measured color profile.
- The report does not claim sensor-derived Log, ten-bit fidelity, film-stock
  fidelity, cinema-camera equivalence, or fixed cadence without measured
  evidence.
- No Kotlin, Gradle, or workflow sources were changed.
