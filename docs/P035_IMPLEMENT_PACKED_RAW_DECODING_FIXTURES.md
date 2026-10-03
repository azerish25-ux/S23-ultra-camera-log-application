# P035 — implement packed RAW decoding fixtures

Active phase: **P035**. Entry gate: **P034**.

This note publishes a host fixture for packed RAW decoding. It does **not**
measure a physical Galaxy S23. A green host run is not that measurement and
is not physical S23 qualification.

## Deliverable

Packing adapters and exact golden arrays.

Machine-readable fixture:
[P035_IMPLEMENT_PACKED_RAW_DECODING_FIXTURES.json](P035_IMPLEMENT_PACKED_RAW_DECODING_FIXTURES.json)
(`schemaVersion` 1, `phase` `P035`, `mapId` `s23-packed-raw-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is a 4×4 checkerboard of minimum and maximum codes for
`RAW_SENSOR`, `RAW10`, and `RAW12`, each with row padding and a crop that
begins at `(1, 1)`. All four CFA parities (`RGGB`, `GRBG`, `GBRG`, `BGGR`)
are named at absolute buffer coordinates. Padding bytes stay in the row and
are not samples.

`scripts/gates/p035_implement_packed_raw_decoding_fixtures.py` encodes the
phase method, fixture, oracle, and mutant:

- `decode_plane` uses the declared layout. `RAW_SENSOR` is little-endian
  16-bit with stride. `RAW10` packs four pixels into five bytes. `RAW12`
  packs two pixels into three bytes. Those layouts are not interchangeable.
- `assess` returns `decoded` only when codes and CFA coordinates match the
  independent fixture and padding still matches. Decision is never
  `qualified` or `allowed`.
- `reject_mutant` reads each buffer as contiguous native-endian uint16,
  ignoring stride and packing. That reading is `rejected`. The golden
  inventory stays in `preservedResults`.

No demosaic and no color transform run in this phase.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p035*.py' -v
```

The phase test loads the fixture, checks the independent bit reference, and
checks that implementing the mutant (contiguous sixteen-bit native-endian
samples) would fail. Case modules TC-P035-01 through TC-P035-08 are separate
files. This phase module does not call them. The command above runs their
host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- Decoded synthetic codes are not sensor-derived Log, ten-bit fidelity,
  film-stock fidelity, or cinema-camera equivalence.
- A matching host decode is not fixed cadence and is not a saved RAW
  recording rate.
- `RAW_SENSOR`, `RAW10`, and `RAW12` do not share a memory layout.
- Padding, odd-crop CFA phase, and packing boundaries are not color
  processing.
- No Kotlin, Gradle, or workflow sources were changed.
