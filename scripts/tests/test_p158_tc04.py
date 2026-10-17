"""Tests for TC-P158-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p158_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p158_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    return _MODULE.case_payload(**overrides)


class TCP15804(unittest.TestCase):
    def assert_contract(self, result, evidence="p158-advanced-capture"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P158-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_unexecuted_flash_continues_non_destructive_work(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["executed"], False)
        self.assertEqual(_MODULE.CASE["name"], "Missing explicit modification authorization")
        self.assertIn(_GATE.MOTION_RULE, " ".join(result["reasons"]))

    def test_general_app_request_does_not_authorize_a_flash(self):
        result = evaluate(payload(
            executed=True,
            approval="general-app-development",
            continuedNonDestructive=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.UNAUTHORIZED_EXECUTION, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_stopping_non_destructive_work_is_rejected(self):
        result = evaluate(payload(continuedNonDestructive=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NON_DESTRUCTIVE_STOPPED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_fresh_specific_approval_can_be_recorded(self):
        result = evaluate(payload(executed=True, approval="fresh-specific"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_unmeasured_raw_mode_is_rejected_inside_the_case(self):
        result = evaluate(payload(alternativeRawModes=[
            {"id": "raw-12bit", "available": True, "measurementId": None},
        ]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.ALT_RAW_WITHOUT_MEASUREMENT, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p158-tc04-recovery"
        result = evaluate(payload(evidenceId=evidence, repeat="recovery-image"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(approval="implied"))
        with self.assertRaises(ValueError):
            evaluate(payload(operationKind="root"))
