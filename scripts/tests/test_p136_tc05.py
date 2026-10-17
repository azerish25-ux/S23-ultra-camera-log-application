"""Tests for TC-P136-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p136_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p136_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p136-tc05",
        "repeat": "camera",
        "report": _GATE.honest_report(),
        "controlName": "Record",
        "spokenState": "Record, not recording",
        "orderExposed": True,
        "valueExposed": True,
        "cancellationExposed": True,
        "colorOnly": False,
        "precisionGestureOnly": False,
        "unlabeledCanvasOnly": False,
    }
    base.update(overrides)
    return base


class TCP13605(unittest.TestCase):
    def assert_contract(self, result, evidence="p136-tc05"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P136-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertEqual(result["openQuestions"][0], "physical S23 measurement was not run")
        self.assertTrue(result["reasons"])

    def test_constants(self):
        self.assertEqual(_MODULE.CASE["name"], "Nonvisual interaction")
        self.assertEqual(
            _MODULE.CASE["intervention"],
            "Perform the core phase task using accessibility navigation and spoken state information.",
        )
        self.assertEqual(
            _MODULE.CASE["expected"],
            "Expose usable names, order, values, and cancellation without relying only on color or precision gestures.",
        )
        self.assertEqual(
            _MODULE.CASE["negative"],
            "An unlabeled custom canvas as the only control must fail.",
        )
        self.assertEqual(
            _MODULE.CASE["repeat"],
            "Repeat camera operation, ROI selection, focus editing, and recovery export.",
        )

    def test_named_control_is_recorded_as_not_run(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][2]["spokenState"], "Record, not recording")
        self.assertEqual(result["preservedResults"][1]["status"], "not-run")
        self.assertIsNone(result["preservedResults"][1]["shootingWorkflow"])

    def test_unlabeled_canvas_is_rejected(self):
        result = evaluate(payload(unlabeledCanvasOnly=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_color_only_and_missing_cancel_are_rejected(self):
        result = evaluate(payload(colorOnly=True, cancellationExposed=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.COLOR_OR_GESTURE, result["rejectedClaims"])
        self.assertIn(_MODULE.MISSING_SEMANTICS, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_screenshot_approval_is_rejected(self):
        result = evaluate(payload(report=_GATE.honest_report(approved=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.DESKTOP_SCREENSHOT_APPROVAL, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p136-tc05-focus"
        result = evaluate(payload(evidenceId=evidence, repeat="focus", controlName="Focus distance", spokenState="Focus distance 1.5 metres"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(controlName="  "))
        with self.assertRaises(ValueError):
            evaluate(payload(precisionGestureOnly="no"))
