# P010 — ordinary stream map

Active phase: **P010**. Entry gate: **P009**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes the ordinary stream-map fixture and the host gate that exports it.
It does **not** measure a physical Galaxy S23. A green host run is not that
measurement.

## Deliverable

Complete stream map export and timing-aware mode candidates.

Machine-readable fixture: [STREAM_MAP.json](STREAM_MAP.json) (`schemaVersion` 1,
`phase` `P010`, `mapId` `s23-stream-map-fixture`, implementation base
`fffd5c9a63cb732e103052acae29ae0c251585cc`).

This file is the ordinary map only. High-speed and maximum-resolution maps are
separate and are not included here. Sizes and rates in the fixture are authored
constraints, not a camera probe.

`failedProperties` lists `dynamicRangeProfiles`. That failed query does not
empty the stream list. One stream records `queryError` `timing` and stays in
the export beside the other advertised configurations on logical camera `0`,
including 1920×1080 and 3840×2160 in formats such as `YUV_420_888` and `JPEG`.
A larger JPEG and a RAW size with a low maximum rate (a long minimum frame
duration) are retained as facts and are not offered as proven real-time video.

`minFps` and `maxFps` are decimal strings, including `30` and `29.97`. They
are constraints. `fixedCadenceEvidence` is false on every fixture stream.
`aeRangeIncludesNominal` true does not certify native fixed cadence. The
export sets `fixedCadence` to `withheld` unless `fixedCadenceEvidence` is true,
in which case it is `supported`.

`scripts/gates/p010_stream_map.py` (`validate_map`, `export_streams`,
`assess_combination`) enforces that shape:

- `export_streams` returns every stream, including a stream whose `queryError`
  is set. Identity is `WxH:format@logicalId`. Timing strings are copied as
  written.
- `assess_combination` with `constraints_violated` true decides `rejected`.
  `rejectedClaims` are the selected identities. `preservedResults` are all
  exported identities. The decision is never `qualified`. Selecting every
  individually supported stream does not make an illegal combination legal.
- When constraints are not violated and every selected identity exists, the
  decision is `candidate`. Unselected advertised streams stay in
  `preservedResults`.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p010_stream_map.py' -v
```

The test loads `docs/STREAM_MAP.json`, checks that 3840×2160 remains, checks
that the timing-error stream does not erase 1920×1080, checks that fixed
cadence stays withheld, and checks that selecting every stream with
`constraints_violated` rejects the combination without deleting the export.

## Non-claims

- `STREAM_MAP.json` and this note are an authored fixture, not a device probe
  and not a physical S23 measurement.
- **TC-P010-01 through TC-P010-08 are separate modules. This phase did not run
  those modules.** No result from those modules is claimed here.
- A host pass does not certify fixed cadence, real-time RAW video,
  dynamic-range profiles, coexistence of every advertised stream, endurance,
  or any on-device configuration.
- No Kotlin sources were changed.
