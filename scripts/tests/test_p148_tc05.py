"""Tests for TC-P148-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p148_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p148_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="warm starts")
    base.update({
        "thermalActionRequired": False,
        "optionalWorkReduced": False,
        "captureStopped": False,
        "advertisedRateSustained": False,
        "protectionBypassed": False,
    })
    base.update(overrides)
    return base


class TCP14805(unittest.TestCase):
    def assert_contract(self, result, evidence="p148-offline-privacy"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P148-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_idle_thermal_state_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(result["preservedResults"][3]["protectionBypassed"])
        self.assertEqual(_MODULE.CASE["name"], "Thermal safety pressure")

    def test_reducing_optional_work_is_recorded(self):
        result = evaluate(payload(thermalActionRequired=True, optionalWorkReduced=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_bypassing_protection_to_hold_the_rate_is_rejected(self):
        result = evaluate(payload(
            thermalActionRequired=True,
            advertisedRateSustained=True,
            protectionBypassed=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.THERMAL_IGNORED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_ignoring_thermal_action_is_rejected(self):
        result = evaluate(payload(thermalActionRequired=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.THERMAL_IGNORED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p148-tc05-charging"
        result = evaluate(payload(evidenceId=evidence, repeat="charging"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(protectionBypassed="yes"))
