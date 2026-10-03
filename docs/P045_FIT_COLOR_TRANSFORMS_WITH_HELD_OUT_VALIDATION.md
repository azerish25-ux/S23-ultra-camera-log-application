# P045 — fit color transforms with held-out validation

Active phase: **P045**. Entry gate: **P044**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for a camera-to-working color fit. It does **not**
measure a physical Galaxy S23. A green host run is not that measurement and is
not physical S23 qualification.

## Deliverable

Color fitting tool and independent evaluation report.

Machine-readable fixture:
[P045_FIT_COLOR_TRANSFORMS_WITH_HELD_OUT_VALIDATION.json](P045_FIT_COLOR_TRANSFORMS_WITH_HELD_OUT_VALIDATION.json)
(`schemaVersion` 1, `phase` `P045`, `mapId` `s23-held-out-color-fit-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is an identity matrix on linearized chart patches. Training RMSE
is 0 under illuminant D65, inside the 0.02 training limit. Neutral patch
`N18` is preserved. The held-out `saturated-blue` patch under illuminant A
(a second light) has Euclidean error 0.5, above the 0.15 failure threshold.
Natural scenes (skin, saturated fabric, foliage, narrow-band) are listed and
are not training patches. Weighting is `inverse-variance`. The Frobenius
condition of the identity is 3, below the threshold 1000.

`scripts/gates/p045_fit_color_transforms_with_held_out_validation.py` encodes
the phase method, fixture, oracle, and mutant:

- `assess` keeps training errors, held-out errors, and natural scenes in
  separate `preservedResults` tokens. The fixture decision is `limited`.
  `rejectedClaims` are `held-out-saturated-blue` and `second-illuminant`.
  `limited` is not `qualified` and not `allowed`.
- The mutant sole test `training-patches-only` is `rejected` with
  `training-only-validation`, even though `training_only_would_accept` is
  true. Held-out error 0.5 stays in the inventory. A test fails if that
  mutant is implemented as `training_validated`, `qualified`, or `allowed`.
- A singular or ill-conditioned matrix is `rejected`. A held-out error inside
  the failure threshold is `withheld`, not a measured profile.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p045*.py' -v
```

The phase test loads the fixture, checks that training RMSE stays separate
from the held-out saturated-blue failure, and checks that training-only
validation is rejected. Case modules TC-P045-01 through TC-P045-08 are
separate files. This phase module does not call them. The command above runs
their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- A low training error does not validate the fit, does not prove fixed
  cadence, and does not certify sensor-derived Log, ten-bit fidelity, or
  film-stock fidelity.
- The identity matrix and the chart numbers are not cinema-camera equivalence
  and are not a measured camera-to-working profile from a physical capture.
- Natural-scene tokens are an inventory, not a passed color grade.
- No Kotlin, Gradle, or workflow sources were changed.
