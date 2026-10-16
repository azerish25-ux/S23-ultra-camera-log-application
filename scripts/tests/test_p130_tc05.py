"""Tests for TC-P130-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p130_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p130_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def controls():
    return [
        {"name": "source", "value": _GATE.FIXTURE_SOURCE_ID, "cancellable": True},
        {"name": "look", "value": _GATE.FIXTURE_LOOK_ID, "cancellable": True},
        {"name": "record", "value": "Record", "cancellable": False},
    ]


def payload(**overrides):
    base = {
        "evidenceId": "p130-tc05",
        "repeat": "camera operation",
        "committed": _GATE.make_selection(),
        "proposed": _GATE.imax_proposal(),
        "unlabeledCanvasOnly": False,
        "controls": controls(),
    }
    base.update(overrides)
    return base


class TCP13005(unittest.TestCase):
    def assert_contract(self, result, evidence="p130-tc05"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P130-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_named_source_and_look_controls_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        spoken = result["preservedResults"][2]
        self.assertEqual(spoken["controlOrder"], ["source", "look", "record"])
        self.assertTrue(spoken["sourceSpoken"])
        self.assertTrue(spoken["lookSpoken"])
        self.assertEqual(result["preservedResults"][1]["source_id"], _GATE.FIXTURE_SOURCE_ID)
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "unlabeled-canvas-only-control")

    def test_unlabeled_canvas_is_rejected(self):
        result = evaluate(payload(unlabeledCanvasOnly=True, controls=[]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["source_sha256"], _GATE.FIXTURE_SOURCE_SHA256)

    def test_blank_control_name_is_rejected(self):
        result = evaluate(payload(controls=[{"name": " ", "value": "x", "cancellable": True}]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_clearing_the_look_is_spoken_and_source_stays(self):
        proposed = _GATE.make_selection(look_id=None, look_params=None)
        named = [
            {"name": "source", "value": _GATE.FIXTURE_SOURCE_ID, "cancellable": True},
            {"name": "look", "value": "cleared", "cancellable": True},
        ]
        result = evaluate(payload(proposed=proposed, controls=named, repeat="recovery export"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIsNone(result["preservedResults"][1]["look_id"])
        self.assertTrue(result["preservedResults"][1]["source_retained"])
        self.assertEqual(result["preservedResults"][1]["source_transfer"], "bt709")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(controls=[{"name": "source"}]))
