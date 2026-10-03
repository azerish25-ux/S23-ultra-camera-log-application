# P049 — normalize RAW without destroying evidence

Active phase: **P049**. Entry gate: **P033**, **P041**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for signed RAW normalization. It does **not** measure
a physical Galaxy S23. A green host run is not that measurement and is not
physical S23 qualification.

## Deliverable

Signed normalization kernel and reference vectors.

Machine-readable fixture:
[P049_NORMALIZE_RAW_WITHOUT_DESTROYING_EVIDENCE.json](P049_NORMALIZE_RAW_WITHOUT_DESTROYING_EVIDENCE.json)
(`schemaVersion` 1, `phase` `P049`, `mapId` `s23-signed-raw-normalization-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is an authored 6×4 code grid. Black is `64`. The conservative white
estimate is `800`, below sensor saturation `1023`. Column 0 is optical black
and is excluded from clipping counts. The crop `4x2+1+0` starts on an odd
column, so RGGB phase is not reset to red at the crop origin. Codes include
values below black, at black, near white, at the source white reference, beyond
that white estimate, and at saturation.

`scripts/gates/p049_normalize_raw_without_destroying_evidence.py` encodes the
phase method, fixture, oracle, and mutant:

- `linear_ratio` is `(code-black)/(white-black)` as a reduced fraction. It is
  negative below black and greater than one above the white estimate.
- `assess` keeps those signed values, records clipping counts before
  normalization, and decides `signed_reference`. A normalized value of one is
  the source white reference, not a universal scene-white boundary. Sensor
  saturation and export-clip candidates are separate counts.
- `apply_immediate_clamp` rejects the mutant. Preserved norms stay signed.
- `clamp_unit` is the clamp the mutant would have stored. The honest path does
  not write it.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p049*.py' -v
```

The phase test loads the fixture, checks signed reference vectors with an
independent fraction, checks that the odd crop keeps the sensor CFA channel,
and checks that implementing the mutant (clamping every sample into zero-to-one)
would fail. Case modules TC-P049-01 through TC-P049-08 are separate files.
This phase module does not call them. The command above runs their host tests
as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- Signed normalization is not sensor-derived Log, ten-bit fidelity, film-stock
  fidelity, or cinema-camera equivalence.
- A normalized value of one is not scene white and is not a universal display
  limit.
- Export-clip candidates are not the same report as sensor saturation.
- No fixed cadence is claimed. No Kotlin, Gradle, or workflow sources were
  changed.
