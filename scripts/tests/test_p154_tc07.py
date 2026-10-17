"""Tests for TC-P154-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p154_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p154_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="difficult-scene quality")
    base.update({
        "candidateImprovesArtifact": "noise",
        "candidateMemoryBytes": 8_000_000_000,
        "candidateTimeMs": 50_000,
        "memoryBudgetBytes": 2_000_000_000,
        "timeBudgetMs": 5_000,
        "leaderboardRank": 1,
        "tradeoffReported": True,
        "adoptionGate": "fail",
        "baselineRetained": True,
        "replacedBaseline": False,
        "justifiedBy": "none",
    })
    base.update(overrides)
    return base


class TCP15407(unittest.TestCase):
    def assert_contract(self, result, evidence="p154-firmware-hal-survey"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P154-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_over_budget_model_keeps_the_baseline(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][3]["exceedsBudget"])
        self.assertTrue(result["preservedResults"][3]["baselineRetained"])
        self.assertFalse(result["preservedResults"][3]["replacedBaseline"])
        self.assertEqual(_MODULE.CASE["name"], "Advanced model cost regression")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "leaderboard-alone-justifies-replacement")

    def test_leaderboard_alone_cannot_justify_replacement(self):
        result = evaluate(payload(
            justifiedBy="leaderboard",
            replacedBaseline=True,
            baselineRetained=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.GATE_NOT_PASSED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("p154-firmware-hal-survey", result["preservedResults"])

    def test_missing_tradeoff_is_rejected(self):
        result = evaluate(payload(tradeoffReported=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.TRADEOFF_MISSING, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_replacement_after_a_passing_gate_and_tradeoff_is_recorded(self):
        result = evaluate(payload(
            adoptionGate="pass",
            replacedBaseline=True,
            baselineRetained=False,
            justifiedBy="tradeoff-and-gate",
            candidateMemoryBytes=1_000_000,
            candidateTimeMs=100,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertFalse(result["preservedResults"][3]["exceedsBudget"])
        self.assertEqual(result["rejectedClaims"], [])

    def test_kernel_mode_claim_is_still_rejected(self):
        result = evaluate(payload(applyMutant=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.CLAIMS_ALL_MODES, result["rejectedClaims"])
        self.assertIn("mutant rejected: " + _GATE.MUTANT, result["reasons"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p154-tc07-device-load"
        result = evaluate(payload(evidenceId=evidence, repeat="sustained device load"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(candidateMemoryBytes=-1))
        with self.assertRaises(ValueError):
            evaluate(payload(adoptionGate="maybe"))
        with self.assertRaises(ValueError):
            evaluate(payload(leaderboardRank=True))
