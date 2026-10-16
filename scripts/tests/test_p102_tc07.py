"""Tests for TC-P102-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p102_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p102_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p102-evidence",
        "repeat": "mirrors",
        "predictionsUnstable": True,
        "confidenceScore": 0.99,
        "presentedAsCalibratedProbability": False,
        "confidenceCalibrated": False,
        "renderingRelianceReduced": True,
        "calibrationResiduals": [],
        "sceneTag": "mirrors",
    }
    base.update(overrides)
    return base


class TCP10207(unittest.TestCase):
    def assert_contract(self, result, evidence="p102-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P102-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any(item == "physical S23 measurement was not run" for item in result["openQuestions"]))
        self.assertTrue(result["reasons"])

    def test_good_input_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("uncalibrated", result["preservedResults"])

    def test_directive_negative_is_rejected(self):
        result = evaluate(payload(presentedAsCalibratedProbability=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(
            "arbitrary-confidence-score-presented-calibrated-probability",
            result["rejectedClaims"],
        )

    def test_changed_evidence_id_is_preserved(self):
        evidence = "p102-tc07-glass"
        result = evaluate(payload(evidenceId=evidence, repeat="transparent-surfaces", sceneTag="transparent-surfaces"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(confidenceScore=1.4))
