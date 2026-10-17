"""Tests for TC-P135-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p135_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p135_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p135-tc07",
        "repeat": "source-versus-result",
        "comparison": _GATE.make_comparison(),
        "preferenceJudgment": False,
    }
    base.update(overrides)
    return base


class TCP13507(unittest.TestCase):
    def assert_contract(self, result, evidence="p135-tc07"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P135-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_disclosed_transform_difference_can_carry_a_preference(self):
        result = evaluate(payload(preferenceJudgment=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][1]["matchedInputs"])
        self.assertTrue(result["preservedResults"][1]["transfersDiffer"])
        self.assertFalse(result["preservedResults"][2]["unfair"])
        self.assertIn(_GATE.MATCH_RULE, result["reasons"])

    def test_automatic_contrast_boost_is_rejected(self):
        comparison = _GATE.make_comparison(automatic_contrast_boost=True)
        result = evaluate(payload(comparison=comparison, preferenceJudgment=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.AUTOMATIC_CONTRAST_BOOST, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertNotIn(_MODULE.PREFERENCE_UNFAIR, result["rejectedClaims"])
        self.assertFalse(result["preservedResults"][1]["matchedInputs"])

    def test_contrast_boost_with_a_preference_is_rejected(self):
        comparison = _GATE.replace_side(_GATE.make_comparison(), "right", contrast_boost=1.5)
        result = evaluate(payload(comparison=comparison, preferenceJudgment=True, repeat="recipe revisions"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.CONTRAST_NOT_UNITY, result["rejectedClaims"])
        self.assertIn(_MODULE.PREFERENCE_UNFAIR, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["right"]["contrast_boost"], 1.5)

    def test_mismatched_frames_cannot_carry_a_preference(self):
        comparison = _GATE.replace_side(_GATE.make_comparison(), "left", frame_index=2)
        result = evaluate(payload(comparison=comparison, preferenceJudgment=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.MISMATCHED_FRAMES, result["rejectedClaims"])
        self.assertIn(_MODULE.PREFERENCE_UNFAIR, result["rejectedClaims"])
        self.assertNotIn(_GATE.MUTANT_CLAIM, result["rejectedClaims"])

    def test_disclosed_offset_is_recorded(self):
        comparison = _GATE.make_comparison(sync_offset=-3, offset_disclosed=True)
        result = evaluate(payload(
            comparison=comparison,
            preferenceJudgment=True,
            repeat="different output aspect ratios",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(result["preservedResults"][1]["offsetAccepted"])
        self.assertTrue(result["preservedResults"][1]["framesMatch"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(comparison=_GATE.replace_side(_GATE.make_comparison(), "left", frame_index=-1)))
