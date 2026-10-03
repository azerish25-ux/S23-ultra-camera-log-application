# P058 — define gamut and matrix conventions

Active phase: **P058**. Entry gate: **P057**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for gamut and matrix conventions. It does **not**
measure a physical Galaxy S23. A green host run is not that measurement and is
not physical S23 qualification.

## Deliverable

Complete signal descriptor and contradiction tests.

Machine-readable fixture:
[P058_DEFINE_GAMUT_AND_MATRIX_CONVENTIONS.json](P058_DEFINE_GAMUT_AND_MATRIX_CONVENTIONS.json)
(`schemaVersion` 1, `phase` `P058`, `mapId` `s23-gamut-matrix-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture signal is AWG3, LogC3, white point D65. The working-space to AWG3
matrix is the identity, stored as canonical decimal strings (`decimal-string`
precision). That identity is a host stand-in, not an ARRI-published matrix.
BT.709 storage coefficients are `0.2126`, `0.7152`, `0.0722`. They name a YUV
matrix. The embedded descriptor incorrectly says Rec.709 primaries because
those YUV coefficients were used (`derivedFrom` `yuv-coefficients`). The
sidecar text names AWG3 and BT.709 separately, but it is absent, so it is not
applied. LogC4 is outside this profile.

`scripts/gates/p058_define_gamut_and_matrix_conventions.py` encodes the phase
method, fixture, oracle, and mutant:

- `assess` rejects the fixture. `rejectedClaims` are `yuv-not-rgb-primaries`
  and `contradictory-primaries`. `openQuestions` include the explicit sidecar
  requirement. `preservedResults` keep the AWG3 LogC3 signal, the matrix, the
  YUV coefficients, and the wrong declared primaries. The decision is
  `rejected`, not `qualified` and not `allowed`.
- An explicit sidecar that restates AWG3, LogC3, D65, and the YUV id as a
  different fact yields `sidecar_required`. The embedded Rec.709 claim stays
  rejected. `sidecar_required` is not qualification.
- The mutant interpretation `coefficients-as-primaries` is `rejected` with
  `coefficients-as-primaries`, even though
  `coefficients_would_replace_primaries` is true. A test fails if that mutant
  is implemented as `interchangeable`, `qualified`, or `allowed`.
- Reversed matrix direction, a broken white, and LogC4 are `rejected`. A
  consistent AWG3 descriptor is `withheld`, not a measured profile.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p058*.py' -v
```

The phase test loads the fixture, checks that Rec.709 YUV coefficients do not
become Rec.709 primaries, and checks that the mutant is rejected. Case modules
TC-P058-01 through TC-P058-08 are separate files. This phase module does not
call them. The command above runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- The identity matrix is not an ARRI working-space conversion, not LogC4, and
  not cinema-camera equivalence.
- Rejecting a bad primaries tag does not establish sensor-derived Log,
  ten-bit fidelity, film-stock fidelity, or fixed cadence without measured
  evidence.
- BT.709 YUV coefficients are not RGB primaries and do not imply Rec.709
  primaries.
- No Kotlin, Gradle, or workflow sources were changed.
