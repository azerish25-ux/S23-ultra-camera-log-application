# P060 — implement P010 packing and stride handling

Active phase: **P060**. Entry gate: **P059**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for ten-bit P010 plane geometry. It does **not**
measure a physical Galaxy S23. A green host run is not that measurement and
is not physical S23 qualification.

## Deliverable

P010 writer, reader, and guarded-buffer tests.

Machine-readable fixture:
[P060_IMPLEMENT_P010_PACKING_AND_STRIDE_HANDLING.json](P060_IMPLEMENT_P010_PACKING_AND_STRIDE_HANDLING.json)
(`schemaVersion` 1, `phase` `P060`, `mapId` `s23-p010-packing-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The buffer is 8×4 with row stride 20 and a nonzero crop `(2,2)-(6,4)`. Luma
pixel stride is 2. Chroma is 4:2:0 interleaved with pixel stride 4. Each row
has four padding bytes. The guard byte is 165. Limited-range endpoints are
luma 64 and 940, chroma 64, 512, and 960. Those codes come from distinct
formulas: luma `round(876*E+64)` and chroma `round(896*E+512)`.

`scripts/gates/p060_implement_p010_packing_and_stride_handling.py` encodes the
phase method, fixture, oracle, and mutant:

- `assess` writes only the crop, then an independent unpacker reads the high
  ten bits. On the declared path the decision is `geometry_retained`.
  `preservedResults` keep the crop, strides, intended codes, unpacked codes,
  and the guard and padding flags. `geometry_retained` is not `qualified`
  and not `allowed`.
- The mutant path `store="lsb"` puts each ten-bit code in the low bits of the
  sixteen-bit word. The unpacker still reads the high bits, so the decision
  is `rejected` with `low-bit-ten-bit-store`. Intended codes stay in the
  inventory. A test fails if that mutant is what the declared path returns.
- Unknown plane layouts are `rejected` and are not guessed as a contiguous
  buffer. Bounds and alignment failures are `rejected` before a write.
  Swapped luma and chroma endpoints are `rejected`.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p060*.py' -v
```

The phase test loads the fixture, checks that the independent unpacker
reconstructs the endpoint codes, checks that guard bytes and row padding stay
untouched, and checks that the low-bit mutant is rejected. Case modules
TC-P060-01 through TC-P060-08 are separate files. This phase module does not
call them. The command above runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- `geometry_retained` does not prove fixed cadence, sensor-derived Log,
  ten-bit image fidelity, film-stock fidelity, or cinema-camera equivalence.
- Limited-range formulas are declared conventions. They are not a measured
  camera quantizer.
- Rejecting a low-bit store does not qualify a Main10 bitstream, a physical
  sensor, or a display.
- No Kotlin, Gradle, or workflow sources were changed.
