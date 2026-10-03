# P019 — implement applied manual exposure

Active phase: **P019**. Entry gate: **P018**.

This note publishes a **host fixture** for result-confirmed manual exposure.
It does not measure a physical Galaxy S23. A green host run is not that
measurement, and it is not physical S23 qualification.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This
write-up does not re-run P018 and does not claim that entry gate was freshly
certified here.

## Deliverable

Manual exposure controller and result-matching tests.

| Piece | Path |
| --- | --- |
| Exposure fixture | `docs/P019_IMPLEMENT_APPLIED_MANUAL_EXPOSURE.json` |
| Exposure gate | `scripts/gates/p019_implement_applied_manual_exposure.py` |
| Host tests | `scripts/tests/test_p019_implement_applied_manual_exposure.py` |
| Case modules | `scripts/gates/p019_tc01.py` … `p019_tc08.py` |
| Case tests | `scripts/tests/test_p019_tc01.py` … `test_p019_tc08.py` |
| Handoff | `docs/evidence/P019-handoff.json` |
| This note | `docs/P019_IMPLEMENT_APPLIED_MANUAL_EXPOSURE.md` |

The gate is Python 3 standard library only. It does not use the network and
it does not perform device I/O.

## Method, fixture, oracle, mutant

Method: validate units and sensor limits, clamp only through a visible
effective target, wait for the required lock transition, and compare actual
result values against defined tolerances. Preserve the difference between
missing metadata and a measured mismatch.

Fixture: a requested shutter longer than the frame period and an ISO result
that remains at the previous automatic value.

Oracle: the user sees the effective target and mismatch; recording cannot
claim confirmed manual control.

Mutant: show requested ISO as if it were an observed sensor value.
`presentation` `requested_as_observed` is decision `rejected` with claim
`requested-iso-as-observed`. The observed ISO stays the result value. On this
fixture that is `100`, the previous automatic ISO, not the requested `800`.

## Fixture

`docs/P019_IMPLEMENT_APPLIED_MANUAL_EXPOSURE.json` has `schemaVersion` 1,
`phase` `P019`, `fixtureId` `s23-applied-manual-exposure-fixture`, and
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`.

| Field | Authored value |
| --- | --- |
| Requested ISO | `800` |
| Previous automatic ISO and observed ISO | `100` |
| Requested shutter | `50000000` ns |
| Frame period and visible effective shutter | `33333333` ns |
| Sensor ISO range | `50`–`3200` |
| Lock | required and observed `manual_exposure_locked` |
| AE mode | `off` |
| Presentation | `observed` |

Tolerances are fractions `0.05` for ISO, `0.05` for shutter, and `0.03` for
frame duration. They are host arithmetic, not a calibration.

`scripts/gates/p019_implement_applied_manual_exposure.py`:

- `validate_fixture` checks the authored shape. A shutter minimum above the
  frame period is rejected. Missing metadata must not carry a number, and
  present metadata must.
- `effective_target` clamps ISO to the sensor range and clamps shutter to the
  sensor range and the frame period. The request itself is not rewritten.
  The target is marked visible.
- `assess` returns `caseId`, `decision`, `reasons`, `rejectedClaims`,
  `preservedResults`, and `openQuestions`. Decisions are `withheld`,
  `rejected`, or `result_matched`. They are never `qualified` or `allowed`.
  `confirmed-manual-control` stays in `rejectedClaims`. The inventory of
  request, effective target, observation, and status stays in
  `preservedResults`.

On the authored fixture the decision is `withheld`. The user-visible record
names effective ISO `800`, effective shutter `33333333` ns, and the ISO
mismatch against previous automatic `100`. Missing ISO metadata is a
different status (`missing_metadata`) and is not labeled a measured mismatch.
A numeric match of the visible target is only `result_matched` after the
lock transition and with AE off. That label still rejects confirmed manual
control.

Case modules `evaluate` TC-P019-01 through TC-P019-08. Each encodes that
case's intervention, expected response, and negative control. A negative
control is `rejected`. It is never `qualified` or `allowed`. Preserved
results keep the unaffected evidence.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p019*.py' -v
```

The phase test loads the JSON fixture, checks the long shutter and the ISO
that stayed automatic, checks that missing metadata is not a measured
mismatch, and checks that the mutant does not show requested ISO `800` as
the observed sensor value. Each case test covers at least two repeats from
that case's repetition plan.

## Non-claims

- This note and `P019_IMPLEMENT_APPLIED_MANUAL_EXPOSURE.json` are an authored
  host fixture, not a device probe and not a physical S23 measurement or
  qualification.
- A host pass does not certify fixed cadence, sensor-derived Log, ten-bit
  fidelity, film-stock fidelity, cinema-camera equivalence, or on-device
  Camera2 exposure confirmation.
- `result_matched` is host arithmetic against the visible effective target.
  It is not confirmed manual control and not a physical exposure measurement.
- The phase module does not execute TC-P019-01 through TC-P019-08. Those
  modules are separate host evaluators. Their results are not device evidence.
- No Android or Kotlin sources were changed.
- `docs/evidence/P019-handoff.json` has `commit` null and `nextPhase`
  `blocked` because this phase does not publish. That is not physical
  qualification.
