# P034 — pair Images with exact capture metadata

Active phase: **P034**. Entry gate: **P033**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for an exact image/metadata pairing service. It does
**not** measure a physical Galaxy S23. A green host run is not that measurement
and is not physical S23 qualification.

## Deliverable

Exact pairing service and reorder-timeout tests.

Machine-readable fixture:
[P034_PAIR_IMAGES_WITH_EXACT_CAPTURE_METADATA.json](P034_PAIR_IMAGES_WITH_EXACT_CAPTURE_METADATA.json)
(`schemaVersion` 1, `phase` `P034`, `mapId` `s23-exact-pair-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture delivers frames out of callback order. Metadata for `late`
arrives before its Image. Metadata for `early` is delayed until after other
frames and still matches only `1000000000`. Image `absent` has no metadata.
The most recently received metadata when `absent` arrives is `late`; that
attachment is the mutant and is not used.

`scripts/gates/p034_pair_images_with_exact_capture_metadata.py` encodes the
phase method, fixture, oracle, and mutant:

- Pending images and pending metadata are maps keyed by the exact sensor
  timestamp, each bounded by `pendingLimit`.
- Timeout and missing-metadata policies write an explicit gap. They do not
  borrow a neighbour timestamp.
- Duplicate timestamps reject the new event and keep earlier partial results.
- Every copied Image is closed. An unclosed Image does not become a source record.
- `assess(..., strategy="latest")` and `strategy="nearest"` return `rejected`.

The fixture decision is `gapped`, never `qualified` or `allowed`. Exact tokens
keep the exposure, black level, and neutral that share the sensor timestamp.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p034*.py' -v
```

The phase test loads the fixture, checks exact pairs and the absent-frame gap,
and checks that implementing the mutant (latest metadata on each Image) would
fail. Case modules TC-P034-01 through TC-P034-08 are separate files. This
phase module does not call them. The command above runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- Exact host pairs are not fixed cadence, sensor-derived Log, ten-bit
  fidelity, film-stock fidelity, or cinema-camera equivalence.
- A gap policy is not nearest-neighbour or latest-metadata association.
- Closing an Image in the fixture is not evidence that a device buffer was closed.
- No Kotlin, Gradle, or workflow sources were changed.
