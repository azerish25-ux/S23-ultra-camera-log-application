# P050 — implement all CFA parity cases

Active phase: **P050**. Entry gate: **P049**.

This note publishes a host fixture for CFA coordinate parity. It does **not**
measure a physical Galaxy S23. A green host run is not that measurement and is
not physical S23 qualification.

## Deliverable

CFA coordinate utility and exhaustive parity tests.

Machine-readable fixture:
[P050_IMPLEMENT_ALL_CFA_PARITY_CASES.json](P050_IMPLEMENT_ALL_CFA_PARITY_CASES.json)
(`schemaVersion` 1, `phase` `P050`, `mapId` `s23-cfa-parity-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is an odd-offset crop of each Bayer phase `RGGB`, `BGGR`, `GRBG`,
and `GBRG`. Red, green, and blue codes are the constants 17, 400, and 901.
`rggb-odd-left` is odd on x only, so a reset origin mixes both non-green codes
into the green label. Row padding code 7 stays outside the sample plane.
Developed RGB on `rggb-odd-left` is rotated 90 degrees only after
interpretation. No separately verified mosaic transform is included.

`scripts/gates/p050_implement_all_cfa_parity_cases.py` encodes the phase
method, fixture, oracle, and mutant:

- `carried_channel` keeps the sensor origin of a crop. Local `(0, 0)` of an
  odd RGGB crop is blue, not red.
- `demosaic` fills RGB from those carried constants. `rotate_developed` runs
  only on that RGB image.
- `assess` returns `matched` when channel identity agrees with the fixture and
  neither a red-blue swap nor a green checkerboard is present. It is never
  `qualified` or `allowed`.
- `apply_origin_reset` rejects the mutant and keeps the carried inventory.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p050*.py' -v
```

The phase test loads the fixture, checks the carried origin against an
independent phase table, and checks that implementing the mutant (resetting
CFA origin to the top-left of every cropped buffer) would fail. Case modules
TC-P050-01 through TC-P050-08 are separate files. This phase module does not
call them. The command above runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- Matching channel identity on synthetic planes is not sensor-derived Log,
  ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- A flat demosaic of constant codes is not a measured colour profile and not
  a claim of recovered detail.
- Resetting mosaic parity after a crop is not channel identity.
- Rotating developed RGB is not a verified transform of the source mosaic.
- No fixed cadence is claimed. No Kotlin, Gradle, or workflow sources were
  changed.
