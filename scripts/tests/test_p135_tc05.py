"""Tests for TC-P135-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p135_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p135_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def controls_for(comparison, *, frame="auto", offset="auto", cancellable=True):
    frame_value = str(comparison["left"]["frame_index"]) if frame == "auto" else frame
    offset_value = _GATE.format_offset(float(comparison["sync_offset"])) if offset == "auto" else offset
    return [
        {"name": "left-transfer", "value": comparison["left"]["transfer"], "cancellable": cancellable},
        {"name": "right-transfer", "value": comparison["right"]["transfer"], "cancellable": False},
        {"name": "frame", "value": frame_value, "cancellable": False},
        {"name": "sync-offset", "value": offset_value, "cancellable": False},
    ]


def payload(**overrides):
    comparison = overrides.pop("comparison", _GATE.make_comparison())
    base = {
        "evidenceId": "p135-tc05",
        "repeat": "camera operation",
        "comparison": comparison,
        "unlabeledCanvasOnly": False,
        "controls": controls_for(comparison),
    }
    base.update(overrides)
    return base


class TCP13505(unittest.TestCase):
    def assert_contract(self, result, evidence="p135-tc05"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P135-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_spoken_comparison_controls_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        spoken = result["preservedResults"][2]["spoken"]
        self.assertTrue(all(spoken.values()))
        self.assertEqual(
            result["preservedResults"][2]["controlOrder"],
            ["left-transfer", "right-transfer", "frame", "sync-offset"],
        )
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "unlabeled-canvas-only-control")

    def test_unlabeled_canvas_is_rejected(self):
        result = evaluate(payload(unlabeledCanvasOnly=True, controls=[]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_wrong_spoken_frame_is_rejected(self):
        comparison = _GATE.make_comparison()
        result = evaluate(payload(comparison=comparison, controls=controls_for(comparison, frame="0")))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertFalse(result["preservedResults"][2]["spoken"]["frame"])

    def test_disclosed_offset_must_be_spoken(self):
        comparison = _GATE.make_comparison(sync_offset=2, offset_disclosed=True)
        result = evaluate(payload(
            comparison=comparison,
            controls=controls_for(comparison),
            repeat="focus editing",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(result["preservedResults"][1]["offsetAccepted"])
        self.assertEqual(comparison["sync_offset"], 2)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(controls=[{"name": "frame", "value": "24"}]))
