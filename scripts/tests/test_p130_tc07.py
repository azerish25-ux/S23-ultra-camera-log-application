"""Tests for TC-P130-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p130_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p130_tc07.py",
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
        "evidenceId": "p130-tc07",
        "repeat": "source-versus-result",
        "committed": _GATE.make_selection(),
        "proposed": _GATE.imax_proposal(),
        "left": side(),
        "right": side(),
        "mismatchDisclosed": False,
        "preferenceJudgment": False,
    }
    base.update(overrides)
    return base


class TCP13007(unittest.TestCase):
    def assert_contract(self, result, evidence="p130-tc07"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P130-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_aligned_comparison_is_recorded(self):
        result = evaluate(payload(preferenceJudgment=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(result["preservedResults"][2]["mismatch"])
        self.assertEqual(result["preservedResults"][1]["source_transfer"], "bt709")
        self.assertEqual(result["preservedResults"][1]["look_id"], _GATE.FIXTURE_LOOK_ID)
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "auto-enhanced-comparison-side")

    def test_automatic_enhancement_is_rejected(self):
        result = evaluate(payload(right=side(enhanced=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["source_sha256"], _GATE.FIXTURE_SOURCE_SHA256)

    def test_undisclosed_mismatch_cannot_carry_a_preference(self):
        result = evaluate(payload(
            right=side(scale=1.5, transfer="hlg", time=1),
            preferenceJudgment=True,
            mismatchDisclosed=False,
            repeat="recipe revisions",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNDISCLOSED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_disclosed_mismatch_is_recorded(self):
        result = evaluate(payload(
            right=side(scale=1.5),
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
