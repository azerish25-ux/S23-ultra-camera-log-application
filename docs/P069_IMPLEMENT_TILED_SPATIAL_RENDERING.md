# P069 — implement tiled spatial rendering

Active phase: **P069**. Entry gate: **P068**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for a tile planner and a boundary comparison. It does
**not** measure a physical Galaxy S23. A green host run is not that measurement
and is not physical S23 qualification.

## Deliverable

Tile planner and boundary equivalence tests.

Machine-readable fixture:
[P069_IMPLEMENT_TILED_SPATIAL_RENDERING.json](P069_IMPLEMENT_TILED_SPATIAL_RENDERING.json)
(`schemaVersion` 1, `phase` `P069`, `mapId` `s23-tiled-spatial-rendering-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is an 8×8 integer image. A bright impulse of value `1` sits at
`(4, 4)`, the shared corner of four tiles of size 4. Blur and halation are
Chebyshev box filters whose halo is the node's kernel support (`1`, the
maximum kernel on that node). The planner overlap is the sum of those halos
(`2`) because the crop runs only after blur, halation, lens, and grain finish.
Lens and grain are deterministic functions of global coordinates, not a
tile-local seed. Tolerance is `0`.

`scripts/gates/p069_implement_tiled_spatial_rendering.py` encodes the phase
method, fixture, oracle, and mutant:

- `assess` on the declared path decides `assembled_match`. Boundary and corner
  samples match the untiled reference, `max-delta` is `0`, and the coordinate
  field is not a repeated grain block. `assembled_match` is not `qualified`
  and not `allowed`.
- The mutant path `independent-tiles` applies every effect inside each tile
  with no overlap and with tile-local lens and grain coordinates. It decides
  `rejected`, with `seam`, `repeated-grain-block`, `missing-overlap`, and
  `independent-tiles-without-overlap`. The impulse, node halos, and samples
  stay in `preservedResults`. A test fails if that mutant returns
  `assembled_match`.
- Cropping before dependencies, or turning off global coordinates, is
  `rejected`. An impulse that is not on a tile boundary, or a node list that
  drops blur, halation, lens, or grain, is `withheld`.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p069*.py' -v
```

The phase test loads the fixture, checks that the boundary impulse matches the
untiled reference, and checks that independent tiles without overlap do not.
Case modules TC-P069-01 through TC-P069-08 are separate files. This phase
module does not call them. The command above runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- Matching a host raster does not prove fixed cadence, sensor-derived Log,
  ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- `assembled_match` is an integer box comparison. It is not a GPU memory
  bound, a measured optical halation, a cinema-lens measurement, or an
  on-device render.
- Independent tile-local seeds and a missing overlap are not a seam-free
  result. A silent RGBA8 replacement of a high-precision format is not
  accepted by TC-P069-01.
- No Kotlin, Gradle, or workflow sources were changed.
