"""Tests for TC-P133-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p133_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p133_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p133-tc05",
        "repeat": "camera operation",
        "controls": _GATE.fixture_controls(),
        "focusOrder": _GATE.fixture_focus_order(),
    }
    base.update(overrides)
    return base


class TCP13305(unittest.TestCase):
    def assert_contract(self, result, evidence="p133-tc05"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P133-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_named_order_and_cancellation_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        spoken = result["preservedResults"][2]
        self.assertIn("Record", spoken["names"])
        self.assertIn("Stop", spoken["names"])
        self.assertIn("Grey reference ROI", spoken["names"])
        self.assertIn("Cancel development", spoken["names"])
        self.assertEqual(spoken["focusOrder"][0], "record")
        self.assertIn("stop", spoken["focusOrder"])
        self.assertTrue(spoken["cancelAvailable"])
        self.assertEqual(spoken["minimumTargetSize"], 48)
        self.assertTrue(spoken["recipeSeparate"])
        self.assertEqual(spoken["colorOnlyIds"], [])
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "unlabeled-canvas-only-control")

    def test_unlabeled_canvas_is_rejected(self):
        controls = _GATE.fixture_controls()
        controls.append(
            _GATE.make_control(
                "gesture-canvas",
                "",
                "canvas",
                "canvas",
                family="focus",
                group="gesture-canvas",
                state_description="drawn",
            )
        )
        result = evaluate(
            payload(
                controls=controls,
                focusOrder=_GATE.fixture_focus_order() + ["gesture-canvas"],
                repeat="ROI selection",
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn(_GATE.MUTANT, result["reasons"])
        self.assertIn("gesture-canvas", result["preservedResults"][1]["unlabeledCanvasIds"])
        self.assertIn("p133-tc05", result["preservedResults"])

    def test_gesture_only_focus_edit_is_rejected(self):
        controls = _GATE.replace_control(
            _GATE.fixture_controls(), "virtual-focus", path="gesture", role="slider"
        )
        result = evaluate(payload(controls=controls, repeat="focus editing"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.NON_GESTURE_PATH_MISSING, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][2]["gestureOnlyIds"], ["virtual-focus"])

    def test_tiny_control_without_an_alternative_is_rejected(self):
        controls = _GATE.replace_control(_GATE.fixture_controls(), "grey-reference-roi", target_size=20)
        result = evaluate(payload(controls=controls, repeat="recovery export"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.UNDERSIZED_WITHOUT_ALTERNATIVE, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["minimumTargetSize"], 20)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(applyNegative=True))
