"""Tests for TC-P145-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p145_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p145_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    layers = overrides.pop("layers", None)
    base = {
        "evidenceId": "p145-tc05",
        "repeat": "warm-start",
        "thermalActionRequired": True,
        "policy": "stop-capture",
        "optionalWorkReduced": False,
        "captureStopped": True,
        "advertisedRateSustained": False,
        "takePreserved": True,
        "condition": "warm-start",
    }
    base.update(_GATE.layer_fields(layers))
    base.update(overrides)
    return base


class TCP14505(unittest.TestCase):
    def assert_contract(self, result, evidence="p145-tc05"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P145-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_case_text_matches_the_spec(self):
        self.assertEqual(_MODULE.CASE["name"], "Thermal safety pressure")
        self.assertEqual(
            _MODULE.CASE["negative"],
            "Bypassing protection to sustain an advertised rate must fail.",
        )

    def test_stopping_capture_and_keeping_the_take_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][2]["takePreserved"])
        self.assertTrue(result["preservedResults"][2]["followed"])

    def test_reducing_optional_work_is_recorded(self):
        result = evaluate(payload(
            policy="reduce-optional",
            optionalWorkReduced=True,
            captureStopped=False,
            condition="charging",
            repeat="charging",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(result["preservedResults"][2]["followed"])

    def test_bypass_to_sustain_the_advertised_rate_is_rejected(self):
        result = evaluate(payload(
            policy="bypass",
            captureStopped=False,
            optionalWorkReduced=False,
            advertisedRateSustained=True,
            condition="longer-duration",
            repeat="longer-duration",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_sustaining_the_rate_without_protection_is_rejected(self):
        result = evaluate(payload(
            policy="reduce-optional",
            optionalWorkReduced=False,
            captureStopped=False,
            advertisedRateSustained=True,
            condition="combined-rendering",
            repeat="combined-rendering",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.POLICY_IGNORED, result["rejectedClaims"])

    def test_dropping_the_take_is_rejected(self):
        result = evaluate(payload(takePreserved=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.POLICY_IGNORED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p145-tc05-charging"
        result = evaluate(payload(
            evidenceId=evidence,
            policy="reduce-optional",
            optionalWorkReduced=True,
            captureStopped=False,
            condition="charging",
            repeat="charging",
        ))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(policy="ignore"))
