"""Tests for TC-P159-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p159_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p159_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def routes():
    return [
        {"id": "p010", "public": True, "tested": True, "failed": True},
        {"id": "surface", "public": True, "tested": False, "failed": False},
    ]


def payload(**overrides):
    base = _GATE.core_payload(repeat="surface input")
    base.update({
        "routes": routes(),
        "declaredBlocked": False,
        "alternativesEvaluated": False,
    })
    base.update(overrides)
    return base


class TCP15903(unittest.TestCase):
    def assert_contract(self, result, evidence="p159-computational-optics"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P159-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_untested_alternative_does_not_declare_the_goal_blocked(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["untestedPublic"], ["surface"])
        self.assertEqual(_MODULE.CASE["name"], "Unexplored reversible alternative")

    def test_failed_p010_does_not_prove_ten_bit_impossible(self):
        result = evaluate(payload(declaredBlocked=True, alternativesEvaluated=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.ALTERNATIVES_NOT_EVALUATED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_blocking_claim_with_an_untested_public_route_is_rejected(self):
        result = evaluate(payload(declaredBlocked=True, alternativesEvaluated=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ALTERNATIVES_NOT_EVALUATED, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_evaluated_failures_can_record_a_blocked_goal(self):
        rows = [
            {"id": "p010", "public": True, "tested": True, "failed": True},
            {"id": "surface", "public": True, "tested": True, "failed": True},
            {"id": "reduced-geometry", "public": True, "tested": True, "failed": True},
        ]
        result = evaluate(payload(routes=rows, declaredBlocked=True, alternativesEvaluated=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p159-tc03-deferred"
        result = evaluate(payload(evidenceId=evidence, repeat="deferred processing"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            bad = routes()
            bad[1] = {"id": "surface", "public": True, "tested": False, "failed": True}
            evaluate(payload(routes=bad))
        with self.assertRaises(ValueError):
            evaluate(payload(routes=[]))
