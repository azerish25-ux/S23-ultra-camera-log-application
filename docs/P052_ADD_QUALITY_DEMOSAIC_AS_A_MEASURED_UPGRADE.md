# P052 — add quality demosaic as a measured upgrade

Active phase: **P052**. Entry gate: **P051**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for a quality demosaic benchmark. It does **not**
measure a physical Galaxy S23. A green host run is not that measurement and is
not physical S23 qualification.

## Deliverable

Quality demosaic benchmark and algorithm selection decision.

Machine-readable fixture:
[P052_ADD_QUALITY_DEMOSAIC_AS_A_MEASURED_UPGRADE.json](P052_ADD_QUALITY_DEMOSAIC_AS_A_MEASURED_UPGRADE.json)
(`schemaVersion` 1, `phase` `P052`, `mapId` `s23-quality-demosaic-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture samples synthetic independent RGB scenes through a Bayer mosaic.
`bilinear-reference-v1` is the unchanged P051 bilinear reference: known sites
are copied, in-bounds same-channel neighbors at Chebyshev distance 1 are
averaged, and missing samples are omitted rather than read from a stale row.
`edge-aware-v1` estimates missing green along the lower gradient and copies
chroma along the lower-spread direction. Ties fall back to the bilinear
neighborhood. Scenes are fine repeating fabric, a diagonal high-contrast edge,
colored point lights, a slanted edge, plus held-out independent RAW (BGGR)
and low-light hair.

Declared artifacts are false color, zippering, and aliasing. Texture loss and
color delta are regression checks. Edge contrast is reported and is not an
acceptance metric. On this host fixture the candidate improves the declared
artifacts without a texture or color regression, so `assess` returns
`selected`. `selected` is not `qualified` and not `allowed`. The bilinear
reference id stays in `preservedResults` for numerical and lifecycle testing.

`scripts/gates/p052_add_quality_demosaic_as_a_measured_upgrade.py` encodes
the phase method, fixture, oracle, and mutant:

- The mutant sole test `heavy-sharpen` applies a heavy unsharp mask and is
  `rejected` with `sharpen-as-restored-detail`, even though
  `sharpen_would_accept` is true because edge contrast rose. Zippering and
  color scores stay in the inventory. A test fails if that mutant is
  implemented as `restored-detail`, `qualified`, `allowed`, or `selected`.
- A held-out checkerboard that regresses zippering, aliasing, or color is
  `rejected` without dropping the other scenes.
- A declared-artifact shortfall is `withheld`, not an upgrade.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p052*.py' -v
```

The phase test loads the fixture, checks the worked diagonal and point-light
scores, and checks that heavy sharpening is rejected. Case modules
TC-P052-01 through TC-P052-08 are separate files. This phase module does not
call them. The command above runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- Selecting `edge-aware-v1` here does not prove fixed cadence, sensor-derived
  Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- Increased edge contrast is not restored detail and is not a measured
  demosaic upgrade from a physical sensor.
- The synthetic RGB scenes are not independent camera RAW from a Galaxy S23.
- The retained bilinear reference is a host oracle, not a qualified kernel.
- No Kotlin, Gradle, or workflow sources were changed.
