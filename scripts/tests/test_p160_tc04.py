"""Tests for TC-P160-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p160_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p160_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="bootloader changes")
    base.update({
        "operation": "flash",
        "irreversible": True,
        "authorizationBasis": "none",
        "executed": False,
        "continuedNonDestructive": True,
    })
    base.update(overrides)
    return base


class TCP16004(unittest.TestCase):
    def assert_contract(self, result, evidence="p160-evidence-archive"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P160-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_unexecuted_flash_continues_non_destructive_work(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(result["preservedResults"][3]["executed"])
        self.assertEqual(_MODULE.CASE["name"], "Missing explicit modification authorization")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "general-request-authorizes-irreversible-flash")

    def test_general_app_request_does_not_authorize_a_flash(self):
        result = evaluate(payload(authorizationBasis="general-app-request"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertNotIn(_MODULE.OPERATION_EXECUTED, result["rejectedClaims"])

    def test_unapproved_execution_is_rejected(self):
        result = evaluate(payload(executed=True, operation="security-state"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OPERATION_EXECUTED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_fresh_specific_approval_can_execute(self):
        result = evaluate(payload(
            authorizationBasis="fresh-specific",
            executed=True,
            operation="unverified-recovery",
            repeat="unverified recovery images",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_stopping_non_destructive_work_is_rejected(self):
        result = evaluate(payload(continuedNonDestructive=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NONDESTRUCTIVE_STOPPED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p160-tc04-bootloader"
        result = evaluate(payload(evidenceId=evidence, repeat="bootloader changes", operation="bootloader"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(operation="flash", irreversible=False))
        with self.assertRaises(ValueError):
            evaluate(payload(operation="none", irreversible=True))
