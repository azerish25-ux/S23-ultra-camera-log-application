"""Tests for TC-P155-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p155_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p155_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def adoption(**overrides):
    value = {
        "improvesOneArtifact": True,
        "leaderboardAhead": True,
        "memoryWithinBudget": False,
        "timeWithinBudget": False,
        "tradeoffReported": True,
        "baselineRetained": True,
        "adoptionGatePassed": False,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = _GATE.core_payload(repeat="difficult-scene quality")
    base.update({"adoption": adoption()})
    base.update(overrides)
    return base


class TCP15507(unittest.TestCase):
    def assert_contract(self, result, evidence="p155-reversible-alternatives"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P155-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_over_budget_model_keeps_the_baseline(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        preserved = result["preservedResults"][3]
        self.assertTrue(preserved["tradeoffReported"])
        self.assertTrue(preserved["baselineRetained"])
        self.assertFalse(preserved["adoptionGatePassed"])
        self.assertEqual(_MODULE.CASE["name"], "Advanced model cost regression")

    def test_leaderboard_alone_does_not_replace_the_baseline(self):
        result = evaluate(payload(adoption=adoption(baselineRetained=False, improvesOneArtifact=False)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.BASELINE_DROPPED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_omitted_tradeoff_is_rejected(self):
        result = evaluate(payload(adoption=adoption(tradeoffReported=False, leaderboardAhead=False)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.TRADEOFF_OMITTED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_in_budget_improvement_can_pass_the_gate(self):
        result = evaluate(payload(adoption=adoption(
            memoryWithinBudget=True,
            timeWithinBudget=True,
            baselineRetained=False,
            adoptionGatePassed=True,
        )))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p155-tc07-load"
        result = evaluate(payload(evidenceId=evidence, repeat="sustained device load"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(adoption=adoption(memoryWithinBudget="no")))
        with self.assertRaises(ValueError):
            evaluate(payload(adoption={"leaderboardAhead": True}))
