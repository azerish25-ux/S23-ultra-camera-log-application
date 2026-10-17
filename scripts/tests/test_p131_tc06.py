"""Tests for TC-P131-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p131_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p131_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p131-tc06",
        "repeat": "verification",
        "committed": _GATE.make_control(),
        "proposed": _GATE.held_proposal(),
        "progressBannerPercent": 40,
        "verificationComplete": False,
        "publicationComplete": False,
        "remainingStage": "verification",
    }
    base.update(overrides)
    return base


class TCP13106(unittest.TestCase):
    def assert_contract(self, result, evidence="p131-tc06"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P131-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_incomplete_gate_shows_the_remaining_stage(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("remainingStage=verification", result["preservedResults"])
        self.assertEqual(result["preservedResults"][1]["applied"], 180)
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "premature-complete-banner")

    def test_one_hundred_percent_before_verification_is_rejected(self):
        result = evaluate(payload(progressBannerPercent=100))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["draft"], "1.")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_changed_evidence_id_is_preserved(self):
        evidence = "p131-tc06-decode"
        result = evaluate(payload(evidenceId=evidence, repeat="full-decode", remainingStage="full-decode"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(progressBannerPercent=101))
