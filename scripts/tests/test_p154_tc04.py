"""Tests for TC-P154-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p154_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p154_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def operation(**overrides):
    value = {
        "kind": "flash",
        "irreversible": True,
        "executed": False,
        "approval": "general-app-development",
        "treatedAsAuthorized": False,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = _GATE.core_payload(repeat="bootloader changes")
    base.update({
        "operation": operation(),
        "continuesNonDestructiveWork": True,
    })
    base.update(overrides)
    return base


class TCP15404(unittest.TestCase):
    def assert_contract(self, result, evidence="p154-firmware-hal-survey"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P154-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_unexecuted_flash_without_treating_it_as_authorized_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(result["preservedResults"][3]["executed"])
        self.assertTrue(result["preservedResults"][3]["continuesNonDestructiveWork"])
        self.assertEqual(_MODULE.CASE["name"], "Missing explicit modification authorization")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "general-app-request-authorizes-irreversible-flash")

    def test_general_app_request_does_not_authorize_a_flash(self):
        result = evaluate(payload(operation=operation(treatedAsAuthorized=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertNotIn(_MODULE.EXECUTED, result["rejectedClaims"])
        self.assertIn("p154-firmware-hal-survey", result["preservedResults"])

    def test_executed_irreversible_step_is_rejected(self):
        result = evaluate(payload(operation=operation(
            kind="unverified-recovery",
            approval="fresh-specific",
            executed=True,
            treatedAsAuthorized=True,
        )))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.EXECUTED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_stopping_non_destructive_work_is_rejected(self):
        result = evaluate(payload(continuesNonDestructiveWork=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.STOPPED, result["rejectedClaims"])

    def test_claims_all_modes_is_still_rejected(self):
        result = evaluate(payload(claims_all_modes=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.CLAIMS_ALL_MODES, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p154-tc04-security-state"
        result = evaluate(payload(
            evidenceId=evidence,
            repeat="security-state changes",
            operation=operation(kind="security-state"),
        ))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(operation=operation(approval="vague")))
        with self.assertRaises(ValueError):
            evaluate(payload(continuesNonDestructiveWork="yes"))
