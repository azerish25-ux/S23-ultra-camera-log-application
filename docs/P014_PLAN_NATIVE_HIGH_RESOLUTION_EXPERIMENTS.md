# P014 — plan native high-resolution experiments

Active phase: **P014**. Entry gate: **P013**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for the high-resolution experiment matrix. It does
**not** measure a physical Galaxy S23. A green host run is not that measurement.

## Deliverable

High-resolution experiment matrix and source-geometry evidence.

Machine-readable fixture:
[P014_PLAN_NATIVE_HIGH_RESOLUTION_EXPERIMENTS.json](P014_PLAN_NATIVE_HIGH_RESOLUTION_EXPERIMENTS.json)
(`schemaVersion` 1, `phase` `P014`, `matrixId`
`s23-high-resolution-experiment-matrix`, implementation base
`d4deac8fc82832fd23396a01065c5f0bf9da6670`). The fixture also records the phase
method, the renderer-enlarged 7680×4320 fixture sentence, the upscaled-output
oracle, and the container-only mutant that this gate rejects.

Sizes in the fixture are authored constraints, not a camera probe. User targets
stay visible: native 3840×2160 and a file declared as 7680×4320. The declared
8K file's source is 3840×2160, enlarged by the renderer. Crop, binning, and
downsampling rows are separate from that native geometry.

`requiredExperiments` lists independent `capture`, `encode`, `decode`,
`cadence`, `storage`, and `thermal` rows. Every fixture experiment is
`unmeasured`. An unmeasured row does not promise sensor or processing
throughput.

`scripts/gates/p014_plan_native_high_resolution_experiments.py`
(`validate_matrix`, `export_candidates`, `assess_candidate`, `assess_matrix`,
`native_8k_accepted`) enforces that shape:

- `export_candidates` returns every tuple. Renderer enlargement is labelled
  `upscaled output`. `native8kAccepted` is false. A larger container does not
  remove the 4K candidate.
- `assess_matrix` decides `upscaled` for the declared 7680×4320 enlargement.
  Reasons include the acceptance oracle: the result is labelled upscaled
  output and cannot satisfy the native 8K acceptance requirement.
  `rejectedClaims` include `native-8k`. `preservedResults` keep every tuple,
  including the unaffected 4K candidate.
- `native_8k_accepted` does not treat container width and height as native
  resolution. That is the deliberate mutation this gate rejects.
  `assess_matrix(..., container_only=True)` decides `rejected` with claim
  `container-only-native-resolution` and keeps the same preserved inventory.
- Decisions are never `qualified`, `allowed`, or `native_8k`.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p014*.py' -v
```

The phase test loads the fixture, checks that the renderer-enlarged 7680×4320
file is upscaled output, checks that container dimensions alone do not accept
native 8K, and checks that the 4K candidate remains in the preserved inventory.
Case modules `TC-P014-01` through `TC-P014-08` are separate host checks under
the same command. Each module encodes that case's intervention, expected
result, and negative control. A negative control is never `qualified` or
`allowed`. This phase module does not import the case modules.

## Non-claims

- This note and the JSON fixture are a host fixture, not a device probe and
  not a physical S23 measurement.
- The host result does not satisfy native 8K acceptance, native 4K throughput,
  or any unmeasured sensor or processing claim.
- A host pass does not certify fixed cadence, sensor-derived Log, ten-bit
  fidelity, film-stock fidelity, cinema-camera equivalence, endurance, or
  coexistence of every advertised stream.
- Marking an experiment `measured` inside a synthetic payload is still not a
  physical qualification. `native_8k_accepted` stays false.
- No Kotlin sources were changed.
