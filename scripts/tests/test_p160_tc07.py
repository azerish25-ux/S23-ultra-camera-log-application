"""Tests for TC-P160-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p160_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p160_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="difficult-scene quality")
    base.update({
        "largerModel": True,
        "artifactImproved": True,
        "exceedsMemory": True,
        "exceedsTime": False,
        "tradeoffReported": True,
        "baselineRetained": True,
        "adoptionGatePassed": False,
        "leaderboardAlone": False,
        "replaced": False,
    })
    base.update(overrides)
    return base


class TCP16007(unittest.TestCase):
    def assert_contract(self, result, evidence="p160-evidence-archive"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P160-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_retained_baseline_with_a_reported_tradeoff_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][3]["overBudget"])
        self.assertTrue(result["preservedResults"][3]["baselineRetained"])
        self.assertEqual(_MODULE.CASE["name"], "Advanced model cost regression")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "leaderboard-alone-justifies-replacement")

    def test_leaderboard_alone_cannot_replace_the_baseline(self):
        result = evaluate(payload(leaderboardAlone=True, replaced=True, baselineRetained=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.BASELINE_DROPPED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_omitted_tradeoff_is_rejected(self):
        result = evaluate(payload(tradeoffReported=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.TRADEOFF_OMITTED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertNotIn(_MODULE.BASELINE_DROPPED, result["rejectedClaims"])

    def test_adoption_after_the_gate_is_recorded(self):
        result = evaluate(payload(
            adoptionGatePassed=True,
            baselineRetained=False,
            replaced=True,
            exceedsTime=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p160-tc07-load"
        result = evaluate(payload(evidenceId=evidence, repeat="sustained device load"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(largerModel="yes"))
