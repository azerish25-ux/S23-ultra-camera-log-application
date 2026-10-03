# P059 — qualify ten-bit sample fidelity

Active phase: **P059**. Entry gate: **P058**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for a codec precision protocol. It does **not**
measure a physical Galaxy S23. A green host run is not that measurement and
is not physical S23 qualification.

## Deliverable

Codec precision protocol and paired positive-negative controls.

Machine-readable fixture:
[P059_QUALIFY_TEN_BIT_SAMPLE_FIDELITY.json](P059_QUALIFY_TEN_BIT_SAMPLE_FIDELITY.json)
(`schemaVersion` 1, `phase` `P059`, `mapId` `s23-ten-bit-sample-fidelity-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is an authored Main10 / P010 record. The reference ramp contains
unit steps (`1`, `2`, `3`, `5`, `255`, `257`, `1023`). The decoded samples are
those codes quantized to eight bits and expanded back into ten-bit containers
(`(code >> 2) << 2`). Seven codes disagree. Every decoded code is a multiple
of four. SPS `bitDepthLumaMinus8` is `2`, so the bitstream advertises ten-bit
storage. Packed words use the high-six P010 alignment (`code << 6`). The
binding is codec `hevc`, configuration `main10-high-tier-level51`, and
software build `host-fixture-p059`.

`scripts/gates/p059_qualify_ten_bit_sample_fidelity.py` encodes the phase
method, fixture, oracle, and mutant:

- `assess` compares the ramp and inspects SPS depth plus P010 layout. The
  fixture decision is `precision_failed`. `rejectedClaims` is
  `eight-bit-quantized-ramp`. Pair tokens, the mismatch count, the SPS depth,
  and the codec binding stay in `preservedResults`. `precision_failed` is not
  `qualified` and not `allowed`.
- The mutant sole test `sps-bit-depth-alone` is `rejected` with
  `sps-bit-depth-alone`, even when SPS luma depth is 10 and even when the
  numeric codes match. The ramp inventory is not replaced. A test fails if
  that mutant is implemented as `qualified`, `allowed`, or `ten_bit_fidelity`.
- A numeric match on this host fixture is `withheld`. It is not ten-bit
  fidelity. Low-six alignment, a short stride, a Main10 profile whose SPS
  depth is not 10, and a coarse ramp are `rejected`.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p059*.py' -v
```

The phase test loads the fixture, checks that the eight-bit expansion fails
precision while SPS still advertises ten-bit storage, and checks that
accepting fidelity from SPS bit depth alone is rejected. Case modules
TC-P059-01 through TC-P059-08 are separate files. This phase module does not
call them. The command above runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- `precision_failed`, `withheld`, and `rejected` do not certify ten-bit
  fidelity, sensor-derived Log, film-stock fidelity, or cinema-camera
  equivalence.
- SPS bit depth, a Main10 profile, and a P010 container do not establish
  useful sample precision. The eight-bit negative control is the point of
  the fixture.
- A host numeric match is not fixed cadence, not physical S23 capture, and
  not a measured codec qualification. Qualification would bind a codec,
  configuration, and software build; this fixture does not claim that binding
  for a device.
- No Kotlin, Gradle, or workflow sources were changed.
