"""Tests for TC-P156-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p156_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p156_tc04.py",
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
        "executed": False,
        "authorizationSource": "none",
    })
    base.update(overrides)
    return base


class TCP15604(unittest.TestCase):
    def assert_contract(self, result, evidence="p156-firmware-risk-gate"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P156-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])
        self.assertFalse(result["preservedResults"][1]["proceed"])

    def test_unexecuted_flash_without_authorization_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(result["preservedResults"][3]["executed"])
        self.assertEqual(result["preservedResults"][3]["authorizationSource"], "none")
        self.assertEqual(_MODULE.CASE["name"], "Missing explicit modification authorization")

    def test_general_app_request_does_not_authorize_the_flash(self):
        result = evaluate(payload(authorizationSource="general-app-request"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_executing_the_operation_is_rejected(self):
        result = evaluate(payload(operation="bootloader", executed=True, authorizationSource="device-specific"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.EXECUTED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_device_specific_source_still_does_not_execute(self):
        result = evaluate(payload(operation="security-state", authorizationSource="device-specific"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertFalse(result["preservedResults"][3]["executed"])
        self.assertFalse(result["preservedResults"][1]["flashAuthorized"])

    def test_user_authorized_false_stays_blocked(self):
        result = evaluate(payload(user_authorized=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(result["preservedResults"][1]["blocked"])
        self.assertIn("recorded as blocked", " ".join(result["reasons"]))

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p156-tc04-recovery"
        result = evaluate(payload(evidenceId=evidence, repeat="unverified recovery images", operation="recovery-image"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(operation="wipe"))
        with self.assertRaises(ValueError):
            evaluate(payload(executed="no"))
