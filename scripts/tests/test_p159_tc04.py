"""Tests for TC-P159-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p159_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p159_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="bootloader changes")
    base.update({
        "operationKind": "flash",
        "irreversible": True,
        "executed": False,
        "freshSpecificApproval": False,
        "generalAppRequest": True,
        "continuedNonDestructive": True,
    })
    base.update(overrides)
    return base


class TCP15904(unittest.TestCase):
    def assert_contract(self, result, evidence="p159-computational-optics"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P159-04")
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
        self.assertTrue(result["preservedResults"][3]["generalAppRequest"])
        self.assertEqual(_MODULE.CASE["name"], "Missing explicit modification authorization")

    def test_general_request_does_not_authorize_execution(self):
        result = evaluate(payload(executed=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.UNEXECUTED_REQUIRED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_fresh_specific_approval_can_execute(self):
        result = evaluate(payload(executed=True, freshSpecificApproval=True, operationKind="bootloader"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_stopping_non_destructive_work_is_rejected(self):
        result = evaluate(payload(continuedNonDestructive=False, operationKind="recovery-image"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NON_DESTRUCTIVE_STOPPED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p159-tc04-security-state"
        result = evaluate(payload(evidenceId=evidence, repeat="security-state changes"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(operationKind="format"))
        with self.assertRaises(ValueError):
            evaluate(payload(executed="yes"))
