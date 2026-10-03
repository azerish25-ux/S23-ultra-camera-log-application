# P042 — measure black response and read noise

Active phase: **P042**. Entry gate: **P041**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for dark-frame black response and signed read noise.
It does **not** measure a physical Galaxy S23. A green host run is not that
measurement and is not physical S23 qualification.

## Deliverable

Black-level model and dark-frame analysis report.

Machine-readable fixture:
[P042_MEASURE_BLACK_RESPONSE_AND_READ_NOISE.json](P042_MEASURE_BLACK_RESPONSE_AND_READ_NOISE.json)
(`schemaVersion` 1, `phase` `P042`, `mapId` `s23-black-response-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is two dark frames at black level 100, exposure 10000000 ns, and
gain 1. After that intentionally high black subtraction the signed mean is
-1/2. Column 3 is a persistent hot column (mean 6/1). Temporal variance of the
other signed residuals is 2/3 dn^2. Uncertainty is 1 dn and does not authorize
clipping. Sensor saturation stays 0 and is not mixed with the normalization
offset, which is not applied.

`scripts/gates/p042_measure_black_response_and_read_noise.py` encodes the
phase method, fixture, oracle, and mutant:

- `assess` keeps signed residuals. `preservedResults` keep both frame sums,
  the signed mean, the hot column, the read-noise variance, and the separate
  saturation and normalization tokens.
- The fixture decision is `bias_detected`, never `qualified` or `allowed`.
  `rejectedClaims` are `negative-black-bias` and `persistent-hot-column`.
- The mutant statistic `clamp-to-zero` is `rejected`. Clamping would turn the
  signed sum -16 into a non-negative sum. The preserved mean stays `-1/2`. A
  test fails if that mutant is implemented as the published statistic.
- A later normalization offset does not enter the black residual. Saturated
  codes are counted as sensor saturation and are dropped from the signed sum.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p042*.py' -v
```

The phase test loads the fixture, checks that the negative mean and hot column
stay visible, and checks that clamping black-subtracted RAW to zero is not the
statistic. Case modules TC-P042-01 through TC-P042-08 are separate files. This
phase module does not call them. The command above runs their host tests as
well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- Clipped non-negative residuals are not a black-level model and are not a
  read-noise result.
- Denoising, normalization, or an attractive dark frame is not sensor
  improvement and is not cinema-camera equivalence.
- The report does not claim fixed cadence, sensor-derived Log, ten-bit
  fidelity, or film-stock fidelity.
- No Kotlin, Gradle, or workflow sources were changed.
