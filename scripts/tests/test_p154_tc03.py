"""Tests for TC-P154-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p154_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p154_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def routes():
    return [
        {"id": "p010", "tested": True, "passed": False, "reversible": True, "tenBit": True},
        {"id": "surface-input", "tested": True, "passed": True, "reversible": True, "tenBit": True},
        {"id": "reduced-geometry", "tested": True, "passed": True, "reversible": True, "tenBit": False},
        {"id": "deferred-processing", "tested": True, "passed": True, "reversible": True, "tenBit": False},
        {"id": "scheduling", "tested": True, "passed": True, "reversible": True, "tenBit": False},
    ]


def payload(**overrides):
    base = _GATE.core_payload(repeat="surface input")
    base.update({
        "routes": routes(),
        "claimsAllTenBitImpossible": False,
        "declaresCaptureGoalBlocked": False,
    })
    base.update(overrides)
    return base


class TCP15403(unittest.TestCase):
    def assert_contract(self, result, evidence="p154-firmware-hal-survey"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P154-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_failed_p010_with_other_routes_tested_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(result["preservedResults"][3]["routes"][0]["passed"])
        self.assertTrue(result["preservedResults"][3]["routes"][1]["passed"])
        self.assertEqual(_MODULE.CASE["name"], "Unexplored reversible alternative")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "one-failed-p010-proves-all-ten-bit-impossible")

    def test_one_failed_p010_does_not_prove_ten_bit_impossible(self):
        rows = routes()
        rows[1]["tested"] = False
        rows[1]["passed"] = False
        result = evaluate(payload(routes=rows, claimsAllTenBitImpossible=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertNotIn(_MODULE.UNTESTED_ALTERNATIVE, result["rejectedClaims"])

    def test_blocked_goal_with_an_untested_route_is_rejected(self):
        rows = routes()
        rows[2]["tested"] = False
        rows[2]["passed"] = False
        result = evaluate(payload(routes=rows, declaresCaptureGoalBlocked=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNTESTED_ALTERNATIVE, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_every_failed_ten_bit_route_does_not_use_the_one_route_negative(self):
        rows = routes()
        rows[1]["passed"] = False
        result = evaluate(payload(routes=rows, claimsAllTenBitImpossible=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_phone_modified_is_still_rejected(self):
        result = evaluate(payload(phone_modified=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.PHONE_MODIFIED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p154-tc03-scheduling"
        result = evaluate(payload(evidenceId=evidence, repeat="scheduling changes"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        rows = routes()
        rows[1]["tested"] = False
        rows[1]["passed"] = True
        with self.assertRaises(ValueError):
            evaluate(payload(routes=rows))
