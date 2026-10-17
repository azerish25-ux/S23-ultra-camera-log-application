"""Tests for TC-P155-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p155_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p155_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def change(**overrides):
    value = {"kind": "flash", "executed": False, "authorization": "none"}
    value.update(overrides)
    return value


def payload(**overrides):
    base = _GATE.core_payload(repeat="bootloader changes")
    base.update({"change": change()})
    base.update(overrides)
    return base


class TCP15504(unittest.TestCase):
    def assert_contract(self, result, evidence="p155-reversible-alternatives"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P155-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_unexecuted_flash_without_authorization_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(result["preservedResults"][3]["executed"])
        self.assertTrue(result["preservedResults"][3]["irreversible"])
        self.assertEqual(_MODULE.CASE["name"], "Missing explicit modification authorization")

    def test_general_app_request_does_not_authorize_a_flash(self):
        result = evaluate(payload(change=change(authorization="general-app-development")))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertNotIn(_MODULE.EXECUTED_TOKEN, result["rejectedClaims"])

    def test_executed_irreversible_change_is_rejected(self):
        result = evaluate(payload(change=change(kind="unverified-recovery", executed=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.EXECUTED_TOKEN, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_application_work_can_continue(self):
        result = evaluate(payload(change=change(
            kind="application-work",
            executed=True,
            authorization="general-app-development",
        )))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertFalse(result["preservedResults"][3]["irreversible"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p155-tc04-security"
        result = evaluate(payload(evidenceId=evidence, repeat="security-state changes"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(change=change(kind="root")))
        with self.assertRaises(ValueError):
            evaluate(payload(change={"kind": "flash"}))
