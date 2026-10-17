"""Tests for TC-P131-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p131_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p131_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p131-tc05",
        "repeat": "focus",
        "committed": _GATE.make_control(),
        "proposed": _GATE.held_proposal(),
        "unlabeledCanvasOnly": False,
        "controls": [
            {
                "name": "shutter",
                "value": "draft 1. applied 180",
                "unit": "deg",
                "cancellable": True,
            },
            {
                "name": "stop",
                "value": "enabled",
                "unit": "deg",
                "cancellable": True,
            },
        ],
    }
    base.update(overrides)
    return base


class TCP13105(unittest.TestCase):
    def assert_contract(self, result, evidence="p131-tc05"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P131-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_named_draft_and_applied_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        spoken = result["preservedResults"][2]
        self.assertEqual(spoken["controlOrder"], ["shutter", "stop"])
        self.assertTrue(spoken["draftSpoken"])
        self.assertEqual(spoken["appliedSpoken"], "180")
        self.assertTrue(spoken["cancellable"])
        self.assertEqual(result["preservedResults"][1]["draft"], "1.")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "unlabeled-canvas-only-control")

    def test_unlabeled_canvas_is_rejected(self):
        result = evaluate(payload(unlabeledCanvasOnly=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["applied"], 180)

    def test_changed_evidence_id_is_preserved(self):
        evidence = "p131-tc05-roi"
        result = evaluate(payload(evidenceId=evidence, repeat="roi"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(controls="shutter"))
