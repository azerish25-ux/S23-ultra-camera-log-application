"""Tests for TC-P153-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p153_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p153_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    return _MODULE.example_payload(**overrides)


class TCP15304(unittest.TestCase):
    def assert_contract(self, result, evidence="p153-blocked-capability"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P153-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_unapproved_flash_stays_unexecuted(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(result["preservedResults"][3]["executed"])
        self.assertTrue(result["preservedResults"][3]["continues_nondestructive_work"])
        self.assertEqual(_MODULE.CASE["name"], "Missing explicit modification authorization")

    def test_general_app_request_does_not_authorize_a_flash(self):
        result = evaluate(payload(authorization="general-app-development"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.GENERAL_AUTH, result["rejectedClaims"])
        self.assertNotIn(_MODULE.UNEXECUTED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_executed_irreversible_step_is_rejected(self):
        result = evaluate(payload(executed=True, authorization="specific"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNEXECUTED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.GENERAL_AUTH, result["rejectedClaims"])

    def test_stopping_app_work_is_rejected(self):
        result = evaluate(payload(continues_nondestructive_work=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CONTINUE_WORK, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p153-tc04-recovery"
        result = evaluate(payload(
            evidenceId=evidence,
            repeat="unverified-recovery",
            operation="unverified-recovery",
        ))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(operation="flash", irreversible=False))
