# P053 — correct defects without erasing real detail

Active phase: **P053**. Entry gate: **P052**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for defect correction beside a real highlight. It
does **not** measure a physical Galaxy S23. A green host run is not that
measurement and is not physical S23 qualification.

## Deliverable

Defect correction policy and highlight-preservation tests.

Machine-readable fixture:
[P053_CORRECT_DEFECTS_WITHOUT_ERASING_REAL_DETAIL.json](P053_CORRECT_DEFECTS_WITHOUT_ERASING_REAL_DETAIL.json)
(`schemaVersion` 1, `phase` `P053`, `mapId` `s23-defect-correction-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is a measured hot pixel at `(2,2)` with confidence `9/10`, beside
a specular highlight that moves from `(3,2)` to `(4,4)` to the saturated edge
`(7,1)`. Background is `100`. The intensity threshold is `800`. The local
median of darker neighbors is `100`. Corrections are applied only in
`scene-linear`, and every original sample is retained.

`scripts/gates/p053_correct_defects_without_erasing_real_detail.py` encodes
the phase method, fixture, oracle, and mutant:

- `assess` keeps originals, the defect map, highlight tokens, confidence
  masks, and corrected values in `preservedResults`. The fixture decision is
  `highlight_preserved`. That label is not `qualified` and not `allowed`.
- The mutant sole test `intensity-threshold` is `rejected` with
  `intensity-threshold-removal` and a `removed:` claim for the moving
  highlight. The highlight value stays in the inventory. A test fails if that
  mutant is implemented as `threshold_cleaned`, `highlight_preserved`,
  `qualified`, or `allowed`.
- Low confidence, a failed local test, a discarded original, or a
  non-scene-linear domain does not erase the highlight inventory.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p053*.py' -v
```

The phase test loads the fixture, checks that the hot pixel is corrected while
the moving highlight and the saturated-boundary sample remain, and checks that
one-threshold removal is rejected. Case modules TC-P053-01 through TC-P053-08
are separate files. This phase module does not call them. The command above
runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- Correcting the fixture hot pixel does not prove fixed cadence, sensor-derived
  Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- An intensity threshold is not a measured defect map. Sparse highlights are
  not defects.
- Confidence masks in the fixture are authored fractions, not a sensor
  calibration.
- No Kotlin, Gradle, or workflow sources were changed.
