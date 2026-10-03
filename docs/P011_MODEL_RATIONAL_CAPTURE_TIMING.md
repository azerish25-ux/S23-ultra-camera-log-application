# P011 — rational capture timing

Active phase: **P011**. Entry gate: **P010**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for rational capture timing and the manual-readiness
gate. It does **not** measure a physical Galaxy S23. A green host run is not
that measurement and is not physical S23 qualification.

## Deliverable

Rational timing policy and manual-readiness gate.

Machine-readable fixture:
[P011_MODEL_RATIONAL_CAPTURE_TIMING.json](P011_MODEL_RATIONAL_CAPTURE_TIMING.json)
(`schemaVersion` 1, `phase` `P011`, `policyId` `s23-rational-timing-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is an authored host policy, not a camera probe:

- variable AE range `15/1` through `30/1` frames per second
- requested output `24/1`
- manual timing not confirmed, and no manual frame rate
- container timestamps assigned at `24/1`
- requested exposure `20000000` ns, which fits the effective interval `1/30` s
- no capture result

Rates are reduced numerator/denominator pairs. The AE upper bound stays
`30/1`. It is not rounded to the requested cinematic rate `24/1`. Assigning
container timestamps does not label the candidate native fixed twenty-four.

`scripts/gates/p011_model_rational_capture_timing.py` (`validate_policy`,
`assess_policy`, `retain_ae_upper`, `effective_interval_seconds`,
`exposure_fits`, `classify_mechanism`) enforces that shape:

- Fixed AE (`minFps == maxFps`), variable AE (`minFps < maxFps`), and manual
  frame duration (a frame-rate rational whose reciprocal is the duration) stay
  distinct. The requested output rate is not the sensor mechanism.
- The effective exposure interval is the reciprocal of the mechanism that can
  actually run: the AE maximum rate, or the manual frame rate. A 40 ms
  exposure fits a requested `24/1` output and still exceeds a variable AE
  ceiling of `30/1`.
- Requested exposure above that interval is decision `rejected` with claim
  `exposure-exceeds-interval`. The AE range and the request stay in
  `preservedResults`.
- A missing capture result does not inherit the requested rate. A capture
  result that disagrees with manual or fixed-AE timing is
  `requested-not-applied`. One result inside a variable AE range stays
  `withheld`.
- `assess_policy(..., mutant="round-ae-upper-to-cinematic")` is `rejected`
  with `rounded-ae-upper-bound`. The stated upper bound remains in
  `preservedResults`. `retain_ae_upper` returns that bound unchanged.
- Decisions used here are `withheld`, `rejected`, `manual_ready`, and
  `fixed_ae_observed`. They are never `qualified`, `allowed`, or
  `native_fixed_24`.

`manual_ready` means a host-supplied capture result matches the manual frame
duration and the exposure fits that duration. `fixed_ae_observed` means a
host-supplied capture result matches a fixed AE point. Neither label is
on-device confirmation.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p011*.py' -v
```

The policy test loads `docs/P011_MODEL_RATIONAL_CAPTURE_TIMING.json`, checks
that the 15/1–30/1 range and the 24/1 request are preserved, checks that
container timestamps do not certify native fixed 24, checks that a 40 ms
exposure is rejected against the 30/1 ceiling, and checks that rounding the
AE upper bound to 24 is rejected.

Case modules `scripts/gates/p011_tc01.py` through `p011_tc08.py` are separate.
The policy module does not call them.

## Non-claims

- This fixture, the case modules, and this note are a host gate, not a device
  probe and not a physical S23 measurement. Nothing here qualifies a Galaxy
  S23.
- A host pass does not certify native fixed 24 fps cadence, fixed cadence
  without a measured capture result, sensor-derived Log, ten-bit fidelity,
  film-stock fidelity, or cinema-camera equivalence.
- Assigning constant container timestamps does not upgrade variable sensor
  timing. Rounding an AE upper bound onto a desired cinematic rate is the
  rejected mutant, not the policy.
- `manual_ready` and `fixed_ae_observed` compare rationals in the fixture.
  They are not physical manual confirmation and not cinema-camera equivalence.
- TC-P011-01 through TC-P011-08 do not execute on a phone. Passing them does
  not close endurance, route, codec, or geometry qualification.
- No Kotlin, Gradle, or workflow sources were changed.
- The handoff `commit` field records the implementation base revision
  `d4deac8fc82832fd23396a01065c5f0bf9da6670`. This host step does not create
  a git commit.
