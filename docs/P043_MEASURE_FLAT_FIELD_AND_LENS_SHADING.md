# P043 — measure flat-field and lens shading

Active phase: **P043**. Entry gate: **P042**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for a flat-field acquisition protocol and a
shading-map validator. It does **not** measure a physical Galaxy S23. A green
host run is not that measurement and is not physical S23 qualification.

## Deliverable

Flat-field acquisition protocol and shading-map validator.

Machine-readable fixture:
[P043_MEASURE_FLAT_FIELD_AND_LENS_SHADING.json](P043_MEASURE_FLAT_FIELD_AND_LENS_SHADING.json)
(`schemaVersion` 1, `phase` `P043`, `mapId` `s23-flat-field-shading-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The protocol asks for diffuse uniform illumination, sensor-crop coordinates,
and a separate flat validation capture. The fixture field is a directional
ramp (`0.8`, `0.9`, `1.1`, `1.2`). The authored shading gains stay the
symmetric row `1.04`, `1.01`, `1.01`, `1.04` inside bounds `0.5..2`. Those
gains do not flatten the ramp. The capture crop origin is `1+0` and the map
crop origin is `0+0`.

`scripts/gates/p043_measure_flat_field_and_lens_shading.py` encodes the phase
method, fixture, oracle, and mutant:

- `assess` refuses to absorb a lighting gradient into the lens-shading map
  and records crop-origin mismatch. `preservedResults` keep the session
  metadata, both crops, the field samples, the authored gains, and the
  separate holdout flat.
- The fixture decision is `shading_rejected`, never `qualified` or `allowed`.
  `rejectedClaims` include `illumination-gradient`, `crop-origin-mismatch`,
  and `odd-crop-origin`.
- The mutant application `display-after-rotation` is `rejected`. Shading
  gains are not reprojected into display space. A test fails if that mutant
  is implemented as a pass.
- A uniform field with matching crop, CFA, bounded gains, and a separate
  uniform flat is only `host_consistent`. That label is not physical
  qualification. A non-uniform holdout stays `withheld`.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p043*.py' -v
```

The phase test loads the fixture, checks that the lighting gradient is not
absorbed, and checks that a display-coordinate map after rotation is rejected.
Case modules TC-P043-01 through TC-P043-08 are separate files. This phase
module does not call them. The command above runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- Rejecting this gradient does not certify a universal lens-shading
  correction, a measured flat field, or a cinema-camera spatial profile.
- `host_consistent` does not claim fixed cadence, sensor-derived Log,
  ten-bit fidelity, or film-stock fidelity.
- No Kotlin, Gradle, or workflow sources were changed.
