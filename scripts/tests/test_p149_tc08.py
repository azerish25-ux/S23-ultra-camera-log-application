"""Tests for TC-P149-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p149_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p149_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="capture failure")
    base.update({
        "soleTakeDeleted": False,
        "visualQuality": "excellent",
        "defectFixed": True,
        "regressionExists": True,
        "regressionPasses": True,
        "releaseAllowed": True,
    })
    base.update(overrides)
    return base


class TCP14908(unittest.TestCase):
    def assert_contract(self, result, evidence="p149-thermal-endurance"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P149-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_retained_take_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(result["preservedResults"][3]["soleTakeDeleted"])
        self.assertEqual(_MODULE.CASE["name"], "Critical preservation defect")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "aesthetic-quality-cannot-waive-data-loss")

    def test_excellent_quality_cannot_waive_data_loss(self):
        result = evaluate(payload(
            soleTakeDeleted=True,
            visualQuality="excellent",
            defectFixed=False,
            regressionPasses=False,
            releaseAllowed=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.REGRESSION_OPEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("p149-thermal-endurance", result["preservedResults"])

    def test_fixed_defect_with_a_passing_regression_is_recorded(self):
        result = evaluate(payload(soleTakeDeleted=True, releaseAllowed=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_open_data_loss_without_release_still_blocks(self):
        result = evaluate(payload(
            soleTakeDeleted=True,
            visualQuality="poor",
            defectFixed=False,
            regressionExists=False,
            regressionPasses=False,
            releaseAllowed=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.REGRESSION_OPEN, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_thermal_footage_loss_is_rejected_with_the_case(self):
        result = evaluate(payload(
            thermalStatus="critical",
            continueCapture=False,
            controlledStop=True,
            footagePreserved=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.FOOTAGE_NOT_PRESERVED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p149-tc08-cold-start"
        result = evaluate(payload(evidenceId=evidence, repeat="cold-start recovery"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(soleTakeDeleted="yes"))
