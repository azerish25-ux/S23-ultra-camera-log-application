"""Tests for TC-P145-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p145_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p145_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    layers = overrides.pop("layers", None)
    base = {
        "evidenceId": "p145-tc08",
        "repeat": "capture-failure",
        "soleTakeDeleted": False,
        "visualQuality": 0.99,
        "defectFixed": True,
        "regressionOutcome": "passed",
        "aestheticWaiver": False,
        "regressionCountedAsPassed": False,
        "event": "capture-failure",
    }
    base.update(_GATE.layer_fields(layers))
    base.update(overrides)
    return base


class TCP14508(unittest.TestCase):
    def assert_contract(self, result, evidence="p145-tc08"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P145-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_case_text_matches_the_spec(self):
        self.assertEqual(_MODULE.CASE["name"], "Critical preservation defect")
        self.assertEqual(_MODULE.CASE["negative"], "Aesthetic quality cannot waive a data-loss gate.")

    def test_retained_take_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(result["preservedResults"][2]["blocked"])
        self.assertEqual(result["preservedResults"][1]["totalPassed"], 5)

    def test_excellent_quality_does_not_waive_deletion(self):
        result = evaluate(payload(
            soleTakeDeleted=True,
            defectFixed=False,
            regressionOutcome="failed",
            visualQuality=1.0,
            event="publication-failure",
            repeat="publication-failure",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DATA_LOSS, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_poor_quality_still_blocks_data_loss(self):
        result = evaluate(payload(
            soleTakeDeleted=True,
            defectFixed=False,
            regressionOutcome="failed",
            visualQuality=0.2,
            aestheticWaiver=False,
            event="cancellation",
            repeat="cancellation",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DATA_LOSS, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_fixed_defect_with_a_passing_regression_is_recorded(self):
        result = evaluate(payload(
            soleTakeDeleted=True,
            defectFixed=True,
            regressionOutcome="passed",
            visualQuality=0.95,
            event="cold-start-recovery",
            repeat="cold-start-recovery",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertFalse(result["preservedResults"][2]["blocked"])

    def test_skipped_regression_is_not_a_pass(self):
        result = evaluate(payload(
            soleTakeDeleted=True,
            defectFixed=True,
            regressionOutcome="skipped",
            regressionCountedAsPassed=True,
            visualQuality=0.2,
            aestheticWaiver=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DATA_LOSS, result["rejectedClaims"])
        self.assertIn(_MODULE.SKIP_AS_PASS, result["rejectedClaims"])
        self.assertNotEqual(result["decision"], "qualified")

    def test_release_passed_including_skipped_is_rejected(self):
        result = evaluate(payload(releasePassed=6))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SKIP_AS_PASS, result["rejectedClaims"])
        self.assertIn(_GATE.RELEASE_PASSED_INCLUDES_SKIPPED, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["totalPassed"], 5)

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p145-tc08-recovery"
        result = evaluate(payload(evidenceId=evidence, event="cold-start-recovery", repeat="cold-start-recovery"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(visualQuality=1.2))
        with self.assertRaises(ValueError):
            evaluate(payload(event="aesthetic"))
