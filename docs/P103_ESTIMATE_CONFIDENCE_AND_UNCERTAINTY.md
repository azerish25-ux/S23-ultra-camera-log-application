# P103 — Estimate confidence and uncertainty

Active phase: **P103**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Confidence policy and uncertainty-aware rendering tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Confidence policy and uncertainty-aware rendering tests

- Goal: Prevent uncertain depth from producing unnecessarily aggressive visual artifacts.
- Method: Use available model confidence or explicitly defined proxy measures, consistency checks, and boundary uncertainty. Calibrate thresholds against held-out footage. Confidence controls rendering strength and fallback; it must not be presented as a probability without calibration.
- Fixture: A low-texture wall and a transparent glass edge where repeated estimates vary significantly.
- Oracle: The renderer receives low-confidence regions and can reduce blur instead of forcing an unstable segmentation boundary.
- Mutant that must fail: Treat every depth pixel as equally reliable.

Machine-readable fixture: [P103_ESTIMATE_CONFIDENCE_AND_UNCERTAINTY.json](P103_ESTIMATE_CONFIDENCE_AND_UNCERTAINTY.json).

`scripts/gates/p103_estimate_confidence_and_uncertainty.py` bins each paired
confidence score and absolute depth error into 5 equal bins on [0, 1]. The last
bin includes 1. Accuracy is 1 when the absolute error is within the declared
tolerance and 0 otherwise. Expected calibration error is the unweighted mean,
over non-empty bins only, of `|mean(confidence) - mean(accuracy)|`. Empty bins
are omitted because a bin mean is undefined. A score marked `calibrated` without
a calibration set id and bin counts is rejected. A calibrated claim whose ECE
exceeds `maxEce` is rejected. High-error samples with a narrower mean uncertainty
interval than low-error samples are rejected. Missing confidence metadata stays
`uncalibrated` with reliance weight 0 and is recorded, not treated as certain.
The evidence id stays in `preservedResults`. The decision is never `qualified`
or `allowed`. Scores are not physical probabilities.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p103*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P103-01 through TC-P103-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
