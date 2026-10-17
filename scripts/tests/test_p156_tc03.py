"""Tests for TC-P156-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p156_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p156_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def routes():
    return [
        {"id": "p010-image", "kind": "p010", "tested": True, "failed": True},
        {"id": "surface", "kind": "surface", "tested": False, "failed": False},
        {"id": "reduced", "kind": "reduced-geometry", "tested": False, "failed": False},
    ]


def payload(**overrides):
    base = _GATE.core_payload(repeat="surface input")
    base.update({"routes": routes(), "goalDeclaredBlocked": False})
    base.update(overrides)
    return base


class TCP15603(unittest.TestCase):
    def assert_contract(self, result, evidence="p156-firmware-risk-gate"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P156-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_untested_alternatives_keep_the_goal_open(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["untested"], ["surface", "reduced"])
        self.assertFalse(result["preservedResults"][3]["goalDeclaredBlocked"])
        self.assertEqual(_MODULE.CASE["name"], "Unexplored reversible alternative")

    def test_one_failed_p010_route_does_not_prove_ten_bit_impossible(self):
        result = evaluate(payload(goalDeclaredBlocked=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.GOAL_BLOCKED_EARLY, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_all_tested_failures_may_record_the_goal_as_blocked(self):
        closed = [
            {"id": "p010-image", "kind": "p010", "tested": True, "failed": True},
            {"id": "surface", "kind": "surface", "tested": True, "failed": True},
            {"id": "reduced", "kind": "reduced-geometry", "tested": True, "failed": True},
        ]
        result = evaluate(payload(routes=closed, goalDeclaredBlocked=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_similar_name_only_is_still_rejected(self):
        result = evaluate(payload(similar_name_only=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.SIMILAR_NAME_ONLY, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p156-tc03-geometry"
        result = evaluate(payload(evidenceId=evidence, repeat="reduced geometry"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        bad = routes()
        bad[1] = {"id": "surface", "kind": "surface", "tested": False, "failed": True}
        with self.assertRaises(ValueError):
            evaluate(payload(routes=bad))
