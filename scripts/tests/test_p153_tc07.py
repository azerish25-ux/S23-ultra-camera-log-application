"""Tests for TC-P153-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p153_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p153_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    return _MODULE.example_payload(**overrides)


class TCP15307(unittest.TestCase):
    def assert_contract(self, result, evidence="p153-blocked-capability"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P153-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_over_budget_model_keeps_the_baseline(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        tradeoff = result["preservedResults"][3]
        self.assertTrue(tradeoff["exceedsBudget"])
        self.assertTrue(tradeoff["overMemory"])
        self.assertTrue(tradeoff["overTime"])
        self.assertTrue(tradeoff["artifact_improved"])
        self.assertTrue(tradeoff["baselineRetained"])
        self.assertEqual(tradeoff["leaderboard_rank"], 1)
        self.assertFalse(tradeoff["adoption_gate_passed"])
        self.assertEqual(_MODULE.CASE["name"], "Advanced model cost regression")

    def test_leaderboard_rank_alone_cannot_replace_the_baseline(self):
        result = evaluate(payload(replaced_baseline=True, adoption_gate_passed=False, leaderboard_rank=1))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.GATE_NOT_PASSED, result["rejectedClaims"])
        self.assertIn(_MODULE.LEADERBOARD, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_replacement_without_a_rank_still_waits_for_the_gate(self):
        result = evaluate(payload(replaced_baseline=True, adoption_gate_passed=False, leaderboard_rank=None))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.GATE_NOT_PASSED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.LEADERBOARD, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p153-tc07-load"
        result = evaluate(payload(evidenceId=evidence, repeat="sustained-device-load"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(memory_budget_bytes=0))
            evaluate(payload(leaderboard_rank=0))
