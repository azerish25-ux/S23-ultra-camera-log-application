"""Tests for TC-P102-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p102_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p102_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p102-evidence",
        "repeat": "rapid-camera-movement",
        "sourceTimestamp": 1200,
        "resultTimestamp": 1040,
        "sourceCrop": [0, 0, 1920, 1080],
        "resultCrop": [10, 4, 1900, 1060],
        "policy": "reject",
        "reprojectValidated": False,
        "depthValues": [0.2, 0.5, 0.9],
    }
    base.update(overrides)
    return base


class TCP10206(unittest.TestCase):
    def assert_contract(self, result, evidence="p102-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P102-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any(item == "physical S23 measurement was not run" for item in result["openQuestions"]))
        self.assertTrue(result["reasons"])

    def test_good_input_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("identity:stale", result["preservedResults"])

    def test_directive_negative_is_rejected(self):
        result = evaluate(payload(policy="apply"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("float-array-without-temporal-geometric-identity", result["rejectedClaims"])

    def test_changed_evidence_id_is_preserved(self):
        evidence = "p102-tc06-cut"
        result = evaluate(payload(evidenceId=evidence, repeat="scene-cuts"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(depthValues=[]))
