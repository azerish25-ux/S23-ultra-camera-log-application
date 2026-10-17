"""Tests for TC-P134-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p134_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p134_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def controls(progress="indeterminate", stage="verification"):
    return [
        {"name": "progress", "value": progress, "cancellable": True},
        {"name": "stage", "value": stage, "cancellable": False},
    ]


def payload(**overrides):
    base = {
        "evidenceId": "p134-tc05",
        "repeat": "camera operation",
        "progress": _GATE.fixture_progress(),
        "unlabeledCanvasOnly": False,
        "controls": controls(),
    }
    base.update(overrides)
    return base


class TCP13405(unittest.TestCase):
    def assert_contract(self, result, evidence="p134-tc05"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P134-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_named_progress_controls_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][2]["spokenProgress"], "indeterminate")
        self.assertTrue(result["preservedResults"][2]["progressSpoken"])

    def test_unlabeled_canvas_is_rejected(self):
        result = evaluate(payload(unlabeledCanvasOnly=True, repeat="ROI selection"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_spoken_hundred_percent_does_not_match_indeterminate_progress(self):
        result = evaluate(payload(controls=controls(progress="100 percent")))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PROGRESS_NOT_SPOKEN, result["rejectedClaims"])

    def test_fraction_is_spoken_without_claiming_one(self):
        progress = _GATE.fixture_progress(
            stage="rendering",
            accounted_frames=3,
            expected_frames=12,
            displayed_percent=25,
        )
        result = evaluate(payload(
            progress=progress,
            controls=controls(progress="0.25", stage="rendering"),
            repeat="focus editing",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][1]["fraction"], 0.25)
        self.assertNotEqual(result["preservedResults"][1]["fraction"], 1.0)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(controls=[{"name": "progress", "value": "indeterminate"}]))
