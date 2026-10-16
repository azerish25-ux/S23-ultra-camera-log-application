"""Tests for TC-P120-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p120_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p120_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def honest_report(**overrides):
    value = {
        "shutter_angle": 180.0,
        "fps": 24.0,
        "exposure_seconds": (180.0 / 360.0) / 24.0,
        "interpolation_fraction": 0.2,
        "estimated_disclosed": True,
        "stabilization_crop_fraction": 0.0,
        "rolling_shutter_readout": "unknown",
        "correction_applied": False,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p120-evidence",
        "repeat": "Repeat",
        "combinationPassed": True,
        "report": honest_report(),
        "confidence": 0.9,
        "confidenceFloor": 0.4,
        "occlusionPresent": False,
        "artifactScore": 0.1,
        "artifactBound": 0.4,
        "fallbackApplied": False,
        "labelledNative": False,
    }
    base.update(overrides)
    return base


class TCP12004(unittest.TestCase):
    def assert_contract(self, result, evidence="p120-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P120-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_bounded_disclosed_interpolation_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("estimated samples disclosed", result["reasons"])

    def test_native_label_is_rejected(self):
        result = evaluate(payload(labelledNative=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_low_confidence_without_fallback_is_rejected(self):
        result = evaluate(payload(confidence=0.1))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.LOW_CONFIDENCE, result["rejectedClaims"])

    def test_unbounded_occlusion_without_fallback_is_rejected(self):
        result = evaluate(payload(occlusionPresent=True, artifactScore=0.9))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNBOUNDED, result["rejectedClaims"])

    def test_fallback_keeps_a_low_confidence_interval_recorded(self):
        result = evaluate(payload(confidence=0.1, fallbackApplied=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(any("fallback" in item for item in result["reasons"]))

    def test_undisclosed_interpolation_is_rejected(self):
        result = evaluate(payload(report=honest_report(estimated_disclosed=False)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("interpolation-not-disclosed", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p120-specular"
        result = evaluate(payload(evidenceId=evidence, repeat="reflective objects"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
