"""Tests for TC-P159-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p159_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p159_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="difficult-scene quality")
    base.update({"retainedBaseline": True})
    base.update(overrides)
    return base


class TCP15907(unittest.TestCase):
    def assert_contract(self, result, evidence="p159-computational-optics"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P159-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_over_budget_model_retains_the_baseline(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][3]["retainedBaseline"])
        self.assertEqual(result["preservedResults"][3]["costExceeded"], [True])
        self.assertEqual(result["preservedResults"][3]["adopted"], [False])
        self.assertTrue(result["preservedResults"][1]["qualityCostTradeoffReported"])
        self.assertEqual(_MODULE.CASE["name"], "Advanced model cost regression")

    def test_leaderboard_position_alone_is_rejected(self):
        candidate = _GATE.fixture_candidate(
            adopted=True,
            candidate_error=_GATE.FIXTURE_BASELINE_ERROR,
            citedReasons=["benchmark_rank"],
            memoryBytes=400,
            deferredTimeMs=300,
            licenseDeclared=True,
            converted=True,
            difficultScenesValidated=True,
        )
        result = evaluate(payload(candidates=[candidate], retainedBaseline=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_GATE.RANK_ONLY_ADOPTION, result["rejectedClaims"])
        self.assertIn(_GATE.ONLY_RANK_CITED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_improved_error_over_budget_does_not_replace_the_baseline(self):
        candidate = _GATE.fixture_candidate(
            adopted=True,
            licenseDeclared=True,
            converted=True,
            difficultScenesValidated=True,
        )
        result = evaluate(payload(candidates=[candidate], retainedBaseline=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.COST_TRADEOFF_IGNORED, result["rejectedClaims"])
        self.assertIn(_MODULE.BASELINE_NOT_RETAINED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertTrue(result["preservedResults"][1]["candidates"][0]["errorImproved"])

    def test_in_budget_adoption_is_recorded_when_the_baseline_is_not_claimed_retained(self):
        result = evaluate(payload(candidates=[_GATE.adopting_candidate()], retainedBaseline=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][3]["adopted"], [True])
        self.assertEqual(result["preservedResults"][3]["costExceeded"], [False])

    def test_claiming_both_adoption_and_retention_is_rejected(self):
        result = evaluate(payload(candidates=[_GATE.adopting_candidate()], retainedBaseline=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ADOPTION_CONTRADICTS_BASELINE, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p159-tc07-deferred-job"
        result = evaluate(payload(evidenceId=evidence, repeat="deferred job interruption"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(retainedBaseline="yes"))
        with self.assertRaises(ValueError):
            evaluate(payload(candidates=[]))
