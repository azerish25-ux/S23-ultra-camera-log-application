"""Tests for TC-P150-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p150_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p150_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="warm starts")
    base.update({
        "thermalActionRequired": True,
        "optionalWorkReduced": True,
        "captureStopped": False,
        "advertisedRateSustained": False,
        "protectionBypassed": False,
    })
    base.update(overrides)
    return base


class TCP15005(unittest.TestCase):
    def assert_contract(self, result, evidence="p150-signing-distribution"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P150-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_reduced_work_under_thermal_pressure_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][3]["optionalWorkReduced"])
        self.assertEqual(_MODULE.CASE["name"], "Thermal safety pressure")

    def test_bypassing_protection_to_hold_the_rate_is_rejected(self):
        result = evaluate(payload(protectionBypassed=True, advertisedRateSustained=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_ignoring_a_required_thermal_action_is_rejected(self):
        result = evaluate(payload(optionalWorkReduced=False, captureStopped=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.THERMAL_IGNORED, result["rejectedClaims"])

    def test_stopping_capture_is_recorded(self):
        result = evaluate(payload(optionalWorkReduced=False, captureStopped=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_dropped_private_footage_on_update_is_rejected_inside_the_case(self):
        result = evaluate(payload(update_preserves_private_footage=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.PRIVATE_FOOTAGE_LOST, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p150-tc05-charging"
        result = evaluate(payload(evidenceId=evidence, repeat="charging"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(thermalActionRequired="yes"))
