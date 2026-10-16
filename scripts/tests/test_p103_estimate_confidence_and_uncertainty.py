"""Host checks for P103. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p103_estimate_confidence_and_uncertainty",
    Path(__file__).resolve().parents[1] / "gates" / "p103_estimate_confidence_and_uncertainty.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate
expected_calibration_error = _MODULE.expected_calibration_error
intervals_narrow_on_high_error = _MODULE.intervals_narrow_on_high_error
MUTANT = _MODULE.MUTANT
ORACLE = _MODULE.ORACLE
BASE_REVISION = _MODULE.BASE_REVISION

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P103",
        "implementationBaseRevision": "3fbad4bc0e0336e273d2723ec873f001e8865323",
        "evidenceId": "p103-confidence",
        "claim": "synthetic-host-fixture",
        "tolerance": 0.05,
        "maxEce": 0.5,
        "calibrated": False,
        "calibrationSetId": None,
        "binCounts": None,
        "confidenceMetadataPresent": True,
        "pairs": [
            {"confidence": 0.05, "absoluteError": 0.4, "intervalWidth": 0.8},
            {"confidence": 0.15, "absoluteError": 0.3, "intervalWidth": 0.7},
            {"confidence": 0.25, "absoluteError": 0.22, "intervalWidth": 0.55},
            {"confidence": 0.35, "absoluteError": 0.18, "intervalWidth": 0.5},
            {"confidence": 0.45, "absoluteError": 0.12, "intervalWidth": 0.4},
            {"confidence": 0.55, "absoluteError": 0.1, "intervalWidth": 0.36},
            {"confidence": 0.65, "absoluteError": 0.04, "intervalWidth": 0.12},
            {"confidence": 0.75, "absoluteError": 0.03, "intervalWidth": 0.1},
            {"confidence": 0.85, "absoluteError": 0.02, "intervalWidth": 0.06},
            {"confidence": 0.95, "absoluteError": 0.01, "intervalWidth": 0.04},
        ],
        "blurReducedOnLowConfidence": True,
        "applyMutant": False,
    }
    value.update(overrides)
    return value


class P103Tests(unittest.TestCase):
    def test_ece_is_unweighted_mean_of_nonempty_bins(self):
        # Three confident-wrong samples in bin 0 and one confident-wrong sample in bin 4.
        # Unweighted ECE = mean(0.0, 0.8) = 0.4. Count-weighted ECE would be 0.2.
        samples = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (0.8, 1.0)]
        self.assertAlmostEqual(expected_calibration_error(samples, 0.1), 0.4)
        boundary = [(0.2, 0.1)]
        self.assertAlmostEqual(expected_calibration_error(boundary, 0.1), 0.8)
        self.assertAlmostEqual(
            expected_calibration_error([(0.0, 1.0), (0.25, 1.0), (0.5, 0.0), (0.75, 0.0), (1.0, 0.0)], 0.1),
            0.2,
        )

    def test_interval_rule_rejects_only_a_real_inversion(self):
        self.assertFalse(intervals_narrow_on_high_error([(0.4, 0.8), (0.01, 0.1)], 0.05))
        self.assertTrue(intervals_narrow_on_high_error([(0.4, 0.01), (0.01, 0.9)], 0.05))
        self.assertFalse(intervals_narrow_on_high_error([(0.4, 0.2)], 0.05))

    def test_uncalibrated_fixture_is_recorded_not_qualified(self):
        result = assess(document())
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p103-confidence", result["preservedResults"])
        self.assertIn(ORACLE, " ".join(result["reasons"]))
        self.assertTrue(any("physical S23 was not run" in item for item in result["openQuestions"]))
        self.assertTrue(any("not physical probabilities" in item for item in result["reasons"]))
        self.assertTrue(any(item.startswith("expectedCalibrationError=0.260000") for item in result["preservedResults"]))
        self.assertEqual(evaluate(document()), result)

    def test_published_fixture_records(self):
        path = Path(__file__).resolve().parents[2] / "docs" / "P103_ESTIMATE_CONFIDENCE_AND_UNCERTAINTY.json"
        result = assess(json.loads(path.read_text(encoding="utf-8")))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")

    def test_mutant_is_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(MUTANT, result["rejectedClaims"])
        self.assertIn("p103-confidence", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_arbitrary_calibrated_score_is_rejected(self):
        result = assess(document(calibrated=True, calibrationSetId=None, binCounts=None))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("arbitrary-confidence-score-presented-calibrated-probability", result["rejectedClaims"])
        self.assertIn("p103-confidence", result["preservedResults"])

    def test_calibrated_ece_over_max_is_rejected(self):
        result = assess(
            document(
                calibrated=True,
                calibrationSetId="held-out-glass-01",
                binCounts=[2, 2, 2, 2, 2],
                maxEce=0.2,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("expected-calibration-error-exceeds-declared-max", result["rejectedClaims"])
        self.assertIn("synthetic-host-fixture", result["preservedResults"])

    def test_calibrated_score_within_ece_is_recorded_not_a_physical_probability(self):
        result = assess(
            document(
                calibrated=True,
                calibrationSetId="held-out-glass-01",
                binCounts=[1, 0, 0, 0, 1],
                maxEce=0.2,
                pairs=[
                    {"confidence": 0.1, "absoluteError": 0.4, "intervalWidth": 0.8},
                    {"confidence": 0.9, "absoluteError": 0.01, "intervalWidth": 0.05},
                ],
            )
        )
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(any("not a physical probability" in item for item in result["reasons"]))
        self.assertIn("p103-confidence", result["preservedResults"])

    def test_narrow_high_error_intervals_are_rejected(self):
        result = assess(
            document(
                pairs=[
                    {"confidence": 0.1, "absoluteError": 0.4, "intervalWidth": 0.01},
                    {"confidence": 0.9, "absoluteError": 0.01, "intervalWidth": 0.9},
                ]
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("high-error-uncertainty-narrower-than-low-error", result["rejectedClaims"])
        self.assertIn("p103-confidence", result["preservedResults"])

    def test_missing_confidence_metadata_is_recorded_uncalibrated(self):
        result = assess(
            document(
                confidenceMetadataPresent=False,
                pairs=[{"confidence": None, "absoluteError": 0.4, "intervalWidth": 0.8}],
            )
        )
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("status=uncalibrated" in item and "relianceWeight=0" in item for item in result["reasons"]))
        self.assertTrue(any("not treated as certain" in item for item in result["reasons"]))
        self.assertIn("relianceWeight=0.000000", result["preservedResults"])
        self.assertIn("p103-confidence", result["preservedResults"])

    def test_physical_probability_claim_is_rejected(self):
        result = assess(document(claim="a physical probability of depth"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("physical-probability-claimed", result["rejectedClaims"])
        self.assertIn("a physical probability of depth", result["preservedResults"])

    def test_low_confidence_without_blur_reduction_is_rejected(self):
        result = assess(document(blurReducedOnLowConfidence=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("low-confidence-blur-not-reduced", result["rejectedClaims"])

    def test_non_finite_sample_raises(self):
        with self.assertRaises(ValueError):
            assess(document(pairs=[{"confidence": 0.1, "absoluteError": float("nan"), "intervalWidth": 0.2}]))

    def test_invalid_document_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            assess(document(maxEce=1.5))
