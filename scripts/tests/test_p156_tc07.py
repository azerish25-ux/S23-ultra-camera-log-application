"""Tests for TC-P156-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p156_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p156_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="difficult-scene quality")
    base.update({
        "leaderboardRank": 1,
        "qualityGain": 0.04,
        "memoryBytes": 900_000_000,
        "memoryBudget": 512_000_000,
        "timeMs": 40_000,
        "timeBudget": 16_000,
        "baselineRetained": True,
        "replacedBaseline": False,
        "adoptionGatePassed": False,
    })
    base.update(overrides)
    return base


class TCP15607(unittest.TestCase):
    def assert_contract(self, result, evidence="p156-firmware-risk-gate"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P156-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_over_budget_model_keeps_the_baseline(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        preserved = result["preservedResults"][3]
        self.assertTrue(preserved["overBudget"])
        self.assertTrue(preserved["baselineRetained"])
        self.assertFalse(preserved["replacedBaseline"])
        self.assertEqual(preserved["leaderboardRank"], 1)
        self.assertEqual(_MODULE.CASE["name"], "Advanced model cost regression")

    def test_leaderboard_rank_alone_does_not_justify_replacement(self):
        result = evaluate(payload(replacedBaseline=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_replacement_over_budget_is_rejected_even_if_the_gate_claims_to_pass(self):
        result = evaluate(payload(replacedBaseline=True, adoptionGatePassed=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_dropping_the_baseline_is_rejected(self):
        result = evaluate(payload(
            baselineRetained=False,
            replacedBaseline=True,
            adoptionGatePassed=True,
            memoryBytes=100,
            memoryBudget=200,
            timeMs=10,
            timeBudget=20,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.BASELINE_DROPPED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_in_budget_replacement_after_the_gate_can_keep_the_baseline(self):
        result = evaluate(payload(
            replacedBaseline=True,
            adoptionGatePassed=True,
            baselineRetained=True,
            memoryBytes=100,
            memoryBudget=200,
            timeMs=10,
            timeBudget=20,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertFalse(result["preservedResults"][3]["overBudget"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p156-tc07-load"
        result = evaluate(payload(evidenceId=evidence, repeat="sustained device load"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(leaderboardRank=0))
        with self.assertRaises(ValueError):
            evaluate(payload(qualityGain=float("nan")))
