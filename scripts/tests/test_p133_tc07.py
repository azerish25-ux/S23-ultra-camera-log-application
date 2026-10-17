"""Tests for TC-P133-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p133_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p133_tc07.py",
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
        "evidenceId": "p133-tc07",
        "repeat": "source-versus-result",
        "controls": _GATE.fixture_controls(),
        "focusOrder": _GATE.fixture_focus_order(),
        "left": side(),
        "right": side(),
        "mismatchDisclosed": False,
        "preferenceJudgment": False,
    }
    base.update(overrides)
    return base


class TCP13307(unittest.TestCase):
    def assert_contract(self, result, evidence="p133-tc07"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P133-07")
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
        self.assertTrue(result["preservedResults"][1]["recipeSeparate"])
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "auto-enhanced-comparison-side")

    def test_automatic_enhancement_is_rejected(self):
        result = evaluate(payload(right=side(enhanced=True), repeat="recipe revisions"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("p133-tc07", result["preservedResults"])

    def test_undisclosed_mismatch_cannot_carry_a_preference(self):
        result = evaluate(
            payload(
                right=side(scale=1.5, transfer="hlg", time=2),
                preferenceJudgment=True,
                mismatchDisclosed=False,
                repeat="aspect ratios",
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNDISCLOSED, result["rejectedClaims"])
        self.assertTrue(result["preservedResults"][2]["mismatch"])

    def test_disclosed_mismatch_can_be_recorded(self):
        result = evaluate(
            payload(
                left=side(transfer="BT.709"),
                right=side(scale=1.25),
                preferenceJudgment=True,
                mismatchDisclosed=True,
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][2]["mismatch"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(left=side(scale=0)))
        with self.assertRaises(ValueError):
            evaluate(payload(right={"scale": 1}))
