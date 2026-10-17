"""Tests for TC-P157-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p157_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p157_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload()
    base.update({
        "repeat": "bootloader changes",
        "operation": "flash",
        "irreversible": True,
        "executed": False,
        "authorization": "none",
        "nonDestructiveWorkContinues": True,
        "recoveryImageVerified": False,
    })
    base.update(overrides)
    if "experiments" in overrides and "checksum" not in overrides:
        base["checksum"] = _GATE.protocol_checksum(base["experiments"])
    return base


class TCP15704(unittest.TestCase):
    def assert_contract(self, result, evidence="p157-instrumented-experiment-design"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P157-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_unexecuted_flash_without_approval_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(result["preservedResults"][3]["executed"])
        self.assertTrue(result["preservedResults"][3]["nonDestructiveWorkContinues"])
        self.assertEqual(_MODULE.CASE["name"], "Missing explicit modification authorization")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "general-app-request-authorizes-irreversible-flash")

    def test_general_app_request_does_not_authorize_a_flash(self):
        result = evaluate(payload(authorization="general-app-request"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_executing_an_irreversible_operation_is_rejected(self):
        result = evaluate(payload(executed=True, authorization="specific-user-approval"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.EXECUTED_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["expected"], result["reasons"])

    def test_stopping_non_destructive_work_is_rejected(self):
        result = evaluate(payload(nonDestructiveWorkContinues=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.STOPPED_TOKEN, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p157-tc04-bootloader"
        result = evaluate(payload(
            evidenceId=evidence,
            repeat="security-state changes",
            operation="bootloader",
        ))
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
            evaluate(payload(operation="app-development", irreversible=True))
