"""Tests for TC-P120-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p120_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p120_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def honest_report(**overrides):
    exposure = (180.0 / 360.0) / 24.0
    value = {
        "shutter_angle": 180.0,
        "fps": 24.0,
        "exposure_seconds": exposure,
        "interpolation_fraction": 0.0,
        "estimated_disclosed": False,
        "stabilization_crop_fraction": 0.0,
        "rolling_shutter_readout": "unknown",
        "correction_applied": False,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    exposure = (180.0 / 360.0) / 24.0
    base = {
        "evidenceId": "p120-evidence",
        "repeat": "Repeat",
        "combinationPassed": True,
        "report": honest_report(),
        "sourceBlurSeconds": exposure / 2.0,
        "targetExposureSeconds": exposure,
        "claimsExactArbitraryConversion": False,
        "thinMotionUndersampled": False,
    }
    base.update(overrides)
    return base


class TCP12002(unittest.TestCase):
    def assert_contract(self, result, evidence="p120-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P120-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_additional_blur_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any(item.startswith("additionalBlurSeconds=") for item in result["reasons"]))

    def test_exact_conversion_claim_is_rejected(self):
        result = evaluate(payload(claimsExactArbitraryConversion=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_existing_blur_cannot_be_removed(self):
        exposure = (180.0 / 360.0) / 24.0
        result = evaluate(payload(sourceBlurSeconds=exposure * 2.0, targetExposureSeconds=exposure))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CANNOT_RECONSTRUCT, result["rejectedClaims"])

    def test_undersampled_thin_motion_is_rejected(self):
        result = evaluate(payload(thinMotionUndersampled=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNDERSAMPLED, result["rejectedClaims"])

    def test_target_that_disagrees_with_the_report_is_rejected(self):
        result = evaluate(payload(targetExposureSeconds=0.04))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.TARGET_TOKEN, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p120-long-exposure"
        result = evaluate(payload(evidenceId=evidence, repeat="long exposure"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
