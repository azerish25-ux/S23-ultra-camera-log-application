# P047 — validate profiles against independent scenes

Active phase: **P047**. Entry gate: **P046**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for independent profile acceptance. It does **not**
measure a physical Galaxy S23. A green host run is not that measurement and
is not physical S23 qualification.

## Deliverable

Independent profile acceptance suite and limitation statement.

Machine-readable fixture:
[P047_VALIDATE_PROFILES_AGAINST_INDEPENDENT_SCENES.json](P047_VALIDATE_PROFILES_AGAINST_INDEPENDENT_SCENES.json)
(`schemaVersion` 1, `phase` `P047`, `mapId`
`s23-independent-profile-acceptance-fixture`, implementation base
`d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture profile `profile-skin-attractive` has appearance
`preferred-cinematic` and preference `0.92`. Held-out scenes, none used for
fitting, cover skin (repeats `r1` and `r2`), foliage, saturated fabric,
neutral steps, colored light, and high contrast. Training patches
`train-neutral-1` and `train-skin-1` stay disjoint, with training error
`0.006`. Declared tolerances are color `0.04`, exposure `0.05`, noise
`0.08`, highlight `0.03`, and neutral `0.02`.

`fabric-sat` color delta `0.11` fails the color gate. `neutral-grey` neutral
delta `0.08` fails the neutral gate. Exposure, noise, and highlight stay
inside tolerance. Skin preference does not enter the calibration terms and
does not clear either failure.

Limitation: host acceptance is not a phone default, not colorimetric
accuracy, and not physical S23 qualification. Neutral and color failures stay
independent of artistic preference.

`scripts/gates/p047_validate_profiles_against_independent_scenes.py` encodes
the phase method, fixture, oracle, and mutant:

- `calibration_error_terms` lists training error and scene deltas only.
  Preference scores are absent.
- `assess` rejects the fixture. `rejectedClaims` are the failing gates.
  Every scene, training patch, and the preference token stay in
  `preservedResults`. Decision is never `qualified` or `allowed`.
- A copy brought inside every tolerance is `withheld`, not installed as the
  phone default, even when appearance remains `preferred-cinematic`.
- `apply_preferred_appearance_as_accuracy` rejects the mutant and keeps the
  gate failures.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p047*.py' -v
```

The phase test loads the fixture, checks that neutral and color gates fail
independently of preference, and checks that implementing the mutant
(preferred cinematic appearance as colorimetric accuracy) would fail. Case
modules TC-P047-01 through TC-P047-08 are separate files. This phase module
does not call them. The command above runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- A rejected or withheld profile is not camera colorimetric accuracy,
  sensor-derived Log, ten-bit fidelity, film-stock fidelity, or
  cinema-camera equivalence.
- Artistic preference, including a preferred cinematic appearance, is not a
  calibration error term and is not proof of accuracy.
- Passing host gates would still not make the profile the phone default.
- No fixed cadence is claimed. No Kotlin, Gradle, or workflow sources were
  changed.
