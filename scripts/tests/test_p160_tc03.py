"""Tests for TC-P160-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p160_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p160_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="surface input")
    base.update({
        "failedRoute": "P010",
        "alternatives": [{"id": "surface-input", "reversible": True, "tested": True}],
        "captureGoalBlocked": False,
        "claimsAllTenBitImpossible": False,
    })
    base.update(overrides)
    return base


class TCP16003(unittest.TestCase):
    def assert_contract(self, result, evidence="p160-evidence-archive"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P160-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_tested_alternative_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][3]["p010"])
        self.assertEqual(_MODULE.CASE["name"], "Unexplored reversible alternative")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "failed-p010-proves-all-ten-bit-impossible")

    def test_one_failed_p010_route_does_not_prove_ten_bit_impossible(self):
        result = evaluate(payload(claimsAllTenBitImpossible=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertNotIn(_MODULE.ALTERNATIVE_UNEVALUATED, result["rejectedClaims"])

    def test_blocking_the_goal_before_an_alternative_is_rejected(self):
        result = evaluate(payload(
            captureGoalBlocked=True,
            alternatives=[{"id": "surface-input", "reversible": True, "tested": False}],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ALTERNATIVE_UNEVALUATED, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][3]["untestedReversible"], ["surface-input"])

    def test_blocked_goal_after_every_reversible_route_is_recorded(self):
        result = evaluate(payload(captureGoalBlocked=True, failedRoute="camera-interface"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertFalse(result["preservedResults"][3]["p010"])

    def test_only_passes_publication_is_rejected_inside_the_case(self):
        result = evaluate(payload(only_passes=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.ONLY_ATTRACTIVE, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p160-tc03-deferred"
        result = evaluate(payload(evidenceId=evidence, repeat="deferred processing"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(alternatives=[{"id": "x", "tested": True}]))
