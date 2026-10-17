"""Tests for TC-P158-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p158_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p158_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    return _MODULE.case_payload(**overrides)


class TCP15807(unittest.TestCase):
    def assert_contract(self, result, evidence="p158-advanced-capture"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P158-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_over_budget_model_keeps_the_baseline(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["overBudget"], True)
        self.assertEqual(result["preservedResults"][3]["replacedBaseline"], False)
        self.assertEqual(_MODULE.CASE["name"], "Advanced model cost regression")
        self.assertIn(_GATE.MOTION_RULE, " ".join(result["reasons"]))

    def test_leaderboard_alone_is_rejected(self):
        result = evaluate(payload(
            justifiedByLeaderboardOnly=True,
            replacedBaseline=True,
            tradeoffReported=False,
            adoptionGatePassed=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.TRADEOFF_UNREPORTED, result["rejectedClaims"])
        self.assertIn(_MODULE.BASELINE_REPLACED_EARLY, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_replacing_the_baseline_before_the_gate_is_rejected(self):
        result = evaluate(payload(replacedBaseline=True, tradeoffReported=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.BASELINE_REPLACED_EARLY, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_guaranteed_every_scene_is_rejected_inside_the_case(self):
        result = evaluate(payload(guaranteedEveryScene=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.GUARANTEED_EVERY_SCENE, result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p158-tc07-load"
        result = evaluate(payload(evidenceId=evidence, repeat="sustained-device-load"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(leaderboardRank=0))
        with self.assertRaises(ValueError):
            evaluate(payload(memoryBytes=-1))
