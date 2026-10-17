"""Tests for TC-P136-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p136_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p136_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p136-tc07",
        "repeat": "source-versus-result",
        "report": _GATE.honest_report(),
        "leftTime": 1.0,
        "rightTime": 1.0,
        "leftScale": 1.0,
        "rightScale": 1.0,
        "leftTransform": "display-linear",
        "rightTransform": "display-linear",
        "mismatchDisclosed": False,
        "aligned": True,
        "autoEnhancedSide": "none",
        "preferencePresented": True,
    }
    base.update(overrides)
    return base


class TCP13607(unittest.TestCase):
    def assert_contract(self, result, evidence="p136-tc07"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P136-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertEqual(result["openQuestions"][0], "physical S23 measurement was not run")
        self.assertTrue(result["reasons"])

    def test_constants(self):
        self.assertEqual(_MODULE.CASE["name"], "Unfair comparison view")
        self.assertEqual(
            _MODULE.CASE["intervention"],
            "Compare outputs at different times, scales, or display transforms without making those differences visible.",
        )
        self.assertEqual(
            _MODULE.CASE["expected"],
            "Align comparable content or clearly disclose the mismatch before presenting a preference judgment.",
        )
        self.assertEqual(
            _MODULE.CASE["negative"],
            "Automatically enhancing one side of a comparison must fail.",
        )
        self.assertEqual(
            _MODULE.CASE["repeat"],
            "Repeat source-versus-result, recipe revisions, and different output aspect ratios.",
        )

    def test_aligned_comparison_is_recorded_as_not_run(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        view = result["preservedResults"][2]
        self.assertFalse(view["mismatchPresent"])
        self.assertFalse(view["mismatch"]["time"])
        self.assertEqual(result["preservedResults"][1]["status"], "not-run")
        self.assertIsNone(result["preservedResults"][1]["shootingWorkflow"])

    def test_auto_enhanced_side_is_rejected(self):
        result = evaluate(payload(autoEnhancedSide="left"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_undisclosed_time_and_transform_mismatch_is_rejected(self):
        result = evaluate(
            payload(
                rightTime=2.5,
                rightTransform="film-print",
                aligned=False,
                mismatchDisclosed=False,
                preferencePresented=True,
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNDISCLOSED, result["rejectedClaims"])
        self.assertTrue(result["preservedResults"][2]["mismatch"]["time"])
        self.assertTrue(result["preservedResults"][2]["mismatch"]["transform"])
        disclosed = evaluate(
            payload(
                rightScale=0.5,
                aligned=False,
                mismatchDisclosed=True,
                preferencePresented=True,
            )
        )
        self.assertEqual(disclosed["decision"], "recorded")
        self.assertTrue(disclosed["preservedResults"][2]["mismatch"]["scale"])
        self.assertEqual(disclosed["rejectedClaims"], [])

    def test_screenshot_approval_is_rejected(self):
        result = evaluate(payload(report=_GATE.honest_report(approved=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.DESKTOP_SCREENSHOT_APPROVAL, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p136-tc07-aspect"
        result = evaluate(payload(evidenceId=evidence, repeat="aspect"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(autoEnhancedSide="both"))
        with self.assertRaises(ValueError):
            evaluate(payload(leftScale=0))
