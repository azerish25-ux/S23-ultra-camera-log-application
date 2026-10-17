"""Tests for TC-P158-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p158_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p158_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    return _MODULE.case_payload(**overrides)


class TCP15803(unittest.TestCase):
    def assert_contract(self, result, evidence="p158-advanced-capture"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P158-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_failed_p010_with_another_tested_route_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(_MODULE.CASE["name"], "Unexplored reversible alternative")
        self.assertIn(_GATE.MOTION_RULE, " ".join(result["reasons"]))

    def test_failed_p010_does_not_prove_ten_bit_impossible(self):
        result = evaluate(payload(
            routes=[
                {"id": "p010", "tested": True, "failed": True, "reversible": True, "tenBit": True},
                {"id": "surface-input", "tested": False, "failed": False, "reversible": True, "tenBit": True},
            ],
            goalBlocked=True,
            tenBitDeclaredImpossible=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.UNTESTED_REVERSIBLE, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_blocking_the_goal_before_a_reversible_route_is_rejected(self):
        result = evaluate(payload(
            routes=[
                {"id": "p010", "tested": True, "failed": True, "reversible": True, "tenBit": True},
                {"id": "surface-input", "tested": False, "failed": False, "reversible": True, "tenBit": True},
            ],
            goalBlocked=True,
            tenBitDeclaredImpossible=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNTESTED_REVERSIBLE, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_hidden_alignment_is_rejected_inside_the_case(self):
        result = evaluate(payload(
            ghosting={"reported": False, "hidden": True, "magnitude": 0.2},
            alignmentError={"reported": False, "hidden": True, "magnitude": 0.2},
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.HIDDEN_MERGE_ARTIFACT, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p158-tc03-geometry"
        result = evaluate(payload(evidenceId=evidence, repeat="reduced-geometry"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(routes=[]))
        with self.assertRaises(ValueError):
            evaluate(payload(routes=[
                {"id": "p010", "tested": False, "failed": True, "reversible": True, "tenBit": True},
            ]))
