"""Tests for TC-P134-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p134_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p134_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def side(**overrides):
    value = {"scale": 1, "transfer": "bt709", "enhanced": False, "time": 0}
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p134-tc07",
        "repeat": "source-versus-result",
        "progress": _GATE.fixture_progress(),
        "left": side(),
        "right": side(),
        "mismatchDisclosed": False,
        "preferenceJudgment": False,
    }
    base.update(overrides)
    return base


class TCP13407(unittest.TestCase):
    def assert_contract(self, result, evidence="p134-tc07"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P134-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_aligned_comparison_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(result["preservedResults"][2]["mismatch"])
        self.assertIsNone(result["preservedResults"][1]["fraction"])

    def test_automatic_enhancement_is_rejected(self):
        result = evaluate(payload(right=side(enhanced=True), repeat="recipe revisions"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_undisclosed_mismatch_cannot_carry_a_preference(self):
        result = evaluate(payload(
            right=side(scale=0.5, time=1),
            preferenceJudgment=True,
            mismatchDisclosed=False,
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNDISCLOSED, result["rejectedClaims"])

    def test_disclosed_mismatch_is_recorded(self):
        result = evaluate(payload(
            right=side(transfer="hlg"),
            preferenceJudgment=True,
            mismatchDisclosed=True,
            repeat="different output aspect ratios",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(result["preservedResults"][2]["mismatch"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(left=side(scale=0)))
