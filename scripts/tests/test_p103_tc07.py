"""Tests for TC-P103-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p103_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p103_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p103-evidence",
        "repeat": "Repeat",
        "applyNegative": False,
        "applyMutant": False,
        "calibrated": False,
        "calibrationSetId": None,
        "binCounts": None,
        "tolerance": 0.05,
        "maxEce": 0.5,
        "confidenceMetadataPresent": True,
        "blurReducedOnLowConfidence": True,
        "pairs": [
            {"confidence": 0.1, "absoluteError": 0.4, "intervalWidth": 0.8},
            {"confidence": 0.9, "absoluteError": 0.01, "intervalWidth": 0.05},
        ],
    }
    base.update(overrides)
    return base


class TCP10307(unittest.TestCase):
    def assert_contract(self, result, evidence="p103-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P103-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23 was not run" in item for item in result["openQuestions"]))

    def test_clean_result_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("uncalibrated" in item for item in result["reasons"]))
        self.assertTrue(any("not a physical probability" in item or "not physical probabilities" in item for item in result["reasons"]))

    def test_negative_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(applyNegative=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("arbitrary-confidence-score-presented-calibrated-probability", result["rejectedClaims"])

    def test_mutant_is_rejected(self):
        result = evaluate(payload(applyMutant=True, repeat="transparent"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("arbitrary-confidence-score-presented-calibrated-probability", result["rejectedClaims"])

    def test_calibrated_without_set_and_bins_is_rejected(self):
        result = evaluate(payload(calibrated=True, calibrationSetId=None, binCounts=None))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("arbitrary-confidence-score-presented-calibrated-probability", result["rejectedClaims"])

    def test_calibrated_ece_over_max_is_rejected(self):
        result = evaluate(
            payload(
                calibrated=True,
                calibrationSetId="held-out-glass-01",
                binCounts=[1, 0, 0, 0, 1],
                maxEce=0.05,
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("expected-calibration-error-exceeds-declared-max", result["rejectedClaims"])

    def test_narrow_intervals_on_high_error_are_rejected(self):
        result = evaluate(
            payload(
                pairs=[
                    {"confidence": 0.1, "absoluteError": 0.4, "intervalWidth": 0.01},
                    {"confidence": 0.9, "absoluteError": 0.01, "intervalWidth": 0.9},
                ]
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("high-error-uncertainty-narrower-than-low-error", result["rejectedClaims"])

    def test_missing_metadata_stays_uncalibrated_with_zero_reliance(self):
        result = evaluate(
            payload(
                confidenceMetadataPresent=False,
                pairs=[{"confidence": None, "absoluteError": 0.4, "intervalWidth": 0.8}],
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(any("relianceWeight=0" in item and "uncalibrated" in item for item in result["reasons"]))
        self.assertIn("relianceWeight=0.000000", result["preservedResults"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p103-transparent"
        result = evaluate(payload(evidenceId=evidence, repeat="transparent"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(pairs=[{"confidence": 1.4, "absoluteError": 0.0, "intervalWidth": 0.1}]))
