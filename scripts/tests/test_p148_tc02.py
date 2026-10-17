"""Tests for TC-P148-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p148_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p148_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="timestamp pairing")
    base.update({"lineCoverage": 0.91, "faultDetected": True})
    base.update(overrides)
    return base


class TCP14802(unittest.TestCase):
    def assert_contract(self, result, evidence="p148-offline-privacy"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P148-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_detected_fault_is_recorded_even_at_high_coverage(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][3]["faultDetected"])
        self.assertEqual(_MODULE.CASE["name"], "Critical mutant survives")

    def test_high_coverage_without_detection_is_rejected(self):
        result = evaluate(payload(lineCoverage=0.97, faultDetected=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.SURVIVING, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_low_coverage_survivor_is_still_rejected(self):
        result = evaluate(payload(lineCoverage=0.2, faultDetected=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SURVIVING, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_used_permission_without_requirement_is_rejected(self):
        result = evaluate(payload(permissions=[
            {"name": "camera", "required": False, "used": True},
        ], capture_needs_camera=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.USED_NOT_REQUIRED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p148-tc02-range"
        result = evaluate(payload(evidenceId=evidence, repeat="range signalling"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(lineCoverage=1.2))
        with self.assertRaises(ValueError):
            evaluate(payload(faultDetected="yes"))
