"""Tests for TC-P148-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p148_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p148_tc08.py",
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


class TCP14808(unittest.TestCase):
    def assert_contract(self, result, evidence="p148-offline-privacy"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P148-08")
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

    def test_excellent_quality_cannot_waive_data_loss(self):
        result = evaluate(payload(
            soleTakeDeleted=True,
            defectFixed=False,
            regressionPasses=False,
            releaseAllowed=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.REGRESSION_OPEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_open_regression_without_a_waiver_is_still_rejected(self):
        result = evaluate(payload(
            soleTakeDeleted=True,
            visualQuality="poor",
            defectFixed=False,
            regressionPasses=False,
            releaseAllowed=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.REGRESSION_OPEN, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_fixed_defect_with_a_passing_regression_is_recorded(self):
        result = evaluate(payload(soleTakeDeleted=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p148-tc08-cold"
        result = evaluate(payload(evidenceId=evidence, repeat="cold-start recovery"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(soleTakeDeleted="yes"))
