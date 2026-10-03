# P020 — implement stable white-balance controls

Active phase: **P020**. Entry gate: **P019**.

This note publishes a **host fixture** for the white-balance intent model. It
does not measure a physical Galaxy S23. A green host run is not that
measurement, and it is not physical S23 qualification.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This
write-up does not re-run P019 and does not claim that entry gate was freshly
certified here.

## Deliverable

White-balance intent model and capture-versus-look separation.

| Piece | Path |
| --- | --- |
| White-balance fixture | `docs/P020_IMPLEMENT_STABLE_WHITE_BALANCE_CONTROLS.json` |
| Intent model | `scripts/gates/p020_implement_stable_white_balance_controls.py` |
| Focused host tests | `scripts/tests/test_p020_implement_stable_white_balance_controls.py` |
| Case modules | `scripts/gates/p020_tc01.py` … `p020_tc08.py` |
| Case tests | `scripts/tests/test_p020_tc01.py` … `test_p020_tc08.py` |
| Handoff | `docs/evidence/P020-handoff.json` |
| This note | `docs/P020_IMPLEMENT_STABLE_WHITE_BALANCE_CONTROLS.md` |

The gate is Python 3 standard library only. It does not use the network and
it does not perform device I/O.

## Method, fixture, oracle, mutant

Method: expose available presets and locks, record gains and transforms where
accessible, and label Kelvin values provisional unless independently
calibrated. A creative tint slider changes the render recipe, not capture
metadata. Avoid changing the RAW neutral interpretation without versioning
the profile.

Fixture: a stable RAW neutral point with a creative warm preview and an
unsupported hardware Kelvin request.

Oracle: the source metadata stays unchanged, the preview recipe records its
adjustment, and unsupported Kelvin remains unavailable.

Mutant: write a creative temperature slider value into measured sensor
white-balance evidence. `assess_balance(..., mutant=True)` rejects that
claim. Measured Kelvin stays the hardware label. On this fixture that label
is `unavailable`, not the creative slider `3200` and not the look `warm`.

## Model

`docs/P020_IMPLEMENT_STABLE_WHITE_BALANCE_CONTROLS.json` has `schemaVersion`
1, `phase` `P020`, `modelId` `s23-white-balance-intent-fixture`, and
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`.

| Namespace | What it holds | Fixture fact |
| --- | --- | --- |
| `hardware.white_balance` | preset `daylight`, lock engaged, gains `1.84,1.00,1.00,1.52`, transform `sensor-matrix-v1` | Kelvin request `5600` is unsupported and not independently calibrated |
| `raw.neutral` | profile `neutral-v1`, point `0.543,1.00,0.66` | source metadata unchanged; prior profile is the same version |
| `preview.recipe` | temperature `warm`, slider `3200`, tint `plus_8` | adjustment recorded; capture metadata is not written |

Kelvin on this fixture remains unavailable because the hardware request is
not supported, and it is provisional because it is not independently
calibrated. Those are labels, not a colour-temperature measurement.

`scripts/gates/p020_implement_stable_white_balance_controls.py`:

- `validate_model` checks the fixture shape and the three namespaces.
  Hardware, the RAW neutral profile, and the preview recipe stay apart.
  Gains are recorded only when the transform is accessible. Kelvin cannot be
  marked independently calibrated when the hardware request is unsupported.
  Unchanged source metadata cannot carry a new profile version.
- `project_balance` returns hardware evidence, the RAW neutral point, and the
  preview recipe side by side. Measured sensor white balance is the hardware
  preset, the recorded gains, and the hardware Kelvin label. The creative
  slider is not an input. Unsupported Kelvin stays `unavailable`.
- `assess_balance` returns `caseId`, `decision`, `reasons`,
  `rejectedClaims`, `preservedResults`, and `openQuestions`. Decisions are
  `separated`, `withheld`, `versioned`, or `rejected`. They are never
  `qualified` or `allowed`. The mutant, a tint that writes capture metadata,
  a missing preview record, or an unversioned RAW neutral change is
  `rejected`, and the white-balance inventory remains in
  `preservedResults`.

A supported Kelvin value that has not been independently calibrated is
`withheld` and labeled `provisional`. A RAW neutral change that ships a new
profile version is `versioned`. Neither decision is physical qualification.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p020*.py' -v
```

The phase test loads the JSON fixture, checks that source metadata, the
preview recipe, and measured Kelvin stay apart, and checks that the mutant
does not write `3200` or `warm` into measured sensor white-balance evidence. Each case
test covers that case's negative control and at least two repeats from its
repetition plan.

## Cases

The case modules are host evaluations of the P020 repetition plan. They keep
the baseline white-balance inventory (unavailable measured Kelvin, the RAW
neutral point, and the creative preview slider) even when the negative
control fails. None of them returns `qualified` or `allowed`.

| Case | Negative control |
| --- | --- |
| TC-P020-01 Late callback generation | Delayed callback must not resurrect recording or attach an obsolete surface |
| TC-P020-02 Result differs from request | Requested settings must not be shown as measured values |
| TC-P020-03 Interruption during transition | Permanently starting, or a silent capture-contract switch, fails |
| TC-P020-04 Preview consumer stalls | A cosmetic consumer must not block source capture |
| TC-P020-05 Source queue exhaustion | An unbounded queue or hidden frame replacement fails |
| TC-P020-06 Draft control recreation | An invalid partial numeric entry must not reach the camera |
| TC-P020-07 Independent monitoring toggle | A false-color overlay or preview grade must not enter the clean master |
| TC-P020-08 Double stop and repeated cleanup | Double release, duplicate publication, or a second take fails |

`assess_balance` does not execute those modules.

## Non-claims

- This fixture is not a live S23 probe. No physical Galaxy S23 was white
  balanced, opened, or qualified. No sensor, firmware, or on-device session
  is certified by these files.
- Unsupported Kelvin remains `unavailable`. It is not a measured colour
  temperature, and the creative slider `3200` / look `warm` is not sensor
  white-balance evidence.
- A provisional Kelvin label is not independent calibration. Gains in the
  fixture are authored channel ratios, not a spectrophotometer reading.
- The warm preview and tint slider are a render recipe. They are not capture
  metadata and they do not reinterpret the RAW neutral point.
- A versioned profile change is a software label only. It is not film-stock
  fidelity, sensor-derived Log, or ten-bit fidelity.
- A host pass does not certify fixed cadence, cinema-camera equivalence, or
  endurance.
- No Kotlin or Android sources were changed.
- The handoff commit is null and `nextPhase` is `blocked` until publication.
  That is not a claim that P020 is physically complete. The next dependency
  in the directive is P021, and this writer did not publish it.
