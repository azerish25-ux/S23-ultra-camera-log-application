"""Tests for TC-P157-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p157_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p157_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload()
    base.update({
        "repeat": "difficult-scene quality",
        "baseline": {
            "id": "stable-v1",
            "memoryBytes": 1000,
            "timeMs": 50,
            "quality": 0.70,
            "retained": True,
        },
        "candidate": {
            "id": "research-v2",
            "memoryBytes": 8000,
            "timeMs": 400,
            "quality": 0.81,
            "artifactImproved": "noise",
            "leaderboardRank": 1,
        },
        "budgets": {"memoryBytes": 2000, "timeMs": 100},
        "tradeoffReported": True,
        "adoptionGatePassed": False,
        "replacedBaseline": False,
        "checks": {
            "difficultSceneQuality": False,
            "sustainedDeviceLoad": False,
            "deferredJobInterruption": False,
        },
    })
    base.update(overrides)
    if "experiments" in overrides and "checksum" not in overrides:
        base["checksum"] = _GATE.protocol_checksum(base["experiments"])
    return base


class TCP15707(unittest.TestCase):
    def assert_contract(self, result, evidence="p157-instrumented-experiment-design"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P157-07")
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
        self.assertFalse(result["preservedResults"][3]["replacedBaseline"])
        self.assertEqual(_MODULE.CASE["name"], "Advanced model cost regression")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "leaderboard-alone-justifies-replacement")

    def test_leaderboard_rank_alone_does_not_justify_replacement(self):
        result = evaluate(payload(replacedBaseline=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.REPLACED_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_missing_tradeoff_is_rejected(self):
        result = evaluate(payload(tradeoffReported=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.TRADEOFF_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["expected"], result["reasons"])

    def test_dropping_the_baseline_before_the_gate_is_rejected(self):
        baseline = payload()["baseline"]
        baseline["retained"] = False
        result = evaluate(payload(baseline=baseline))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.RETAINED_TOKEN, result["rejectedClaims"])

    def test_adoption_gate_cannot_pass_over_budget(self):
        result = evaluate(payload(adoptionGatePassed=True, checks={
            "difficultSceneQuality": True,
            "sustainedDeviceLoad": True,
            "deferredJobInterruption": True,
        }))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.GATE_TOKEN, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p157-tc07-load"
        result = evaluate(payload(evidenceId=evidence, repeat="sustained device load"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        candidate = payload()["candidate"]
        candidate["leaderboardRank"] = 0
        with self.assertRaises(ValueError):
            evaluate(payload(candidate=candidate))
