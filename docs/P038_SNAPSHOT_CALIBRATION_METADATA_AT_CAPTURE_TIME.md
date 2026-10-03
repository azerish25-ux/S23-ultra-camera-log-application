# P038 — snapshot calibration metadata at capture time

Active phase: **P038**. Entry gate: **P037**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for capture-time calibration snapshots and identity
checks. It does **not** measure a physical Galaxy S23. A green host run is not
that measurement and is not physical S23 qualification.

## Deliverable

Capture-time calibration snapshot and identity checks.

Machine-readable fixture:
[P038_SNAPSHOT_CALIBRATION_METADATA_AT_CAPTURE_TIME.json](P038_SNAPSHOT_CALIBRATION_METADATA_AT_CAPTURE_TIME.json)
(`schemaVersion` 1, `phase` `P038`, `mapId` `s23-capture-calibration-snapshot-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is two authored takes on handset `handset-a`: firmware `fw-1.0.0`
and `fw-2.0.0`, same route, CFA, and crop, different forward matrices. Live
device metadata matches the newer firmware only. `snap-fw1` lists
`calibrationMatrix` and `lensShading` as missing. `snap-fw2` lists
`lensShading` as missing. Missing fields are not backfilled.

Coordinate convention: sensor active-array origin at the top-left, x right, y
down, integer pixels. Crop text is `widthxheight+left+top`. Bayer phase is
relative to the crop origin (`RGGB`, `GRBG`, `GBRG`, `BGGR`).

Matrix convention: row-major 3×3 canonical decimal strings. The forward matrix
maps white-balanced camera RGB to CIE XYZ D50. The calibration matrix maps
device RGB to that reference camera RGB. A snapshot is not a measured profile
and is not an identity-matrix fallback.

`scripts/gates/p038_snapshot_calibration_metadata_at_capture_time.py` encodes
the phase method, fixture, oracle, and mutant:

- `assess` selects each source's bound snapshot. The fixture decision is
  `selected`, never `qualified` or `allowed`.
- `selected_forward` returns the capture-time matrix. Changing live metadata,
  even so its firmware string matches the older take, does not replace it.
- `apply_current_as_truth` rejects the mutant and keeps the capture matrix
  under the `capture:` prefix.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p038*.py' -v
```

The phase test loads the fixture, checks that the older take keeps its own
forward matrix, and checks that implementing the mutant (treating current
camera metadata as capture-time truth) would fail. Case modules TC-P038-01
through TC-P038-08 are separate files. This phase module does not call them.
The command above runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- A selected snapshot is not a measured colour profile, sensor-derived Log,
  ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- Matching handset identity across firmware versions does not make the forward
  matrices interchangeable.
- Current camera metadata is not capture-time truth for an older source.
- `retained_path` in TC-P038-08 is host accounting, not a `qualified` decision
  and not saved-RAW performance on a phone.
- No fixed cadence is claimed. No Kotlin, Gradle, or workflow sources were
  changed.
