# P062 — implement display and Log export branches

Active phase: **P062**. Entry gate: **P061**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for separate clean Log and rendered delivery
branches. It does **not** measure a physical Galaxy S23. A green host run is
not that measurement and is not physical S23 qualification.

## Deliverable

Output graph policies and branch-independence tests.

Machine-readable fixture:
[P062_IMPLEMENT_DISPLAY_AND_LOG_EXPORT_BRANCHES.json](P062_IMPLEMENT_DISPLAY_AND_LOG_EXPORT_BRANCHES.json)
(`schemaVersion` 1, `phase` `P062`, `mapId`
`s23-display-and-log-export-branches-fixture`, implementation base
`d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The take `take-working` is scene-linear RGB `0.2, 1.2, 0.4`. Green is above
diffuse white. The clean branch is named `clean-log`. Its encoding is
`declared-log-fixture`, the host code `(2 * scene + 1) / 4`. It excludes
`film-grain`, `halation`, `virtual-lens`, and `display-tone-map`. It does
not claim LogC3 or a sensor-derived log.

The rendered branch is named `rendered-delivery`. Its recipe is
`strong-grain+halation+virtual-defocus`. Stages, in order, are `film-grain`
(+0.05), `halation` (+0.1 on red), `virtual-defocus` (−0.25 on green), and
`output-transform` `display-film-transform` (clamp to 0..1). Those offsets
are host constants, not a film stock and not a lens.

Honest clean codes are `0.35, 0.85, 0.45`. Honest rendered codes are
`0.35, 1, 0.45`. The clean highlight is not the clamped display of `1.2`.

`scripts/gates/p062_implement_display_and_log_export_branches.py` encodes the
phase method, fixture, oracle, and mutant:

- `assess` on the declared path with selection `clean-log` decides
  `branches_separated`. `preservedResults` keep the working image, the clean
  codes, the exclusion list, the rendered codes, every stage, and the recipe.
  `branches_separated` is not `qualified` and not `allowed`.
- Selection `processed-master` decides `processed_master_named`. The clean
  log is still exported without the rendered recipe. The processed master is
  explicitly named and is not called clean Log.
- The mutant path `display-before-both` clamps the working image to 0..1
  before both branches and still names one output `clean-log`. It decides
  `rejected` with `display-before-both` and `false-clean-log`. Contaminated
  clean codes are `0.35, 0.75, 0.45`. The honest clean codes
  `0.35, 0.85, 0.45` stay in the inventory. A test fails if that mutant is
  what the declared path returns.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p062*.py' -v
```

The phase test loads the fixture, checks that the clean master stays off the
rendered recipe, and checks that the shared display transform is rejected.
Case modules TC-P062-01 through TC-P062-08 are separate files. This phase
module does not call them. The command above runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- Separating two host branches does not prove fixed cadence, sensor-derived
  Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- `declared-log-fixture` is not ARRI LogC3 and not a measured camera log.
- Grain, halation, and virtual defocus are named host offsets, not a
  rendered film stock and not a virtual lens measurement.
- The display clamp is the mutant tone map, not a calibrated display.
- No Kotlin, Gradle, or workflow sources were changed.
