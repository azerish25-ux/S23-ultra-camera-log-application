"""Tests for TC-P129-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p129_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p129_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def _control(ident, name, value, order):
    return {"id": ident, "accessibleName": name, "value": value, "order": order}


def payload(**overrides):
    base = {
        "evidenceId": "p129-tc05",
        "repeat": "camera-operation",
        "controls": [
            _control("record", "Record", "ready", 1),
            _control("stop", "Stop", "idle", 0),
        ],
        "cancellation": "Cancel",
        "colorOnly": False,
        "precisionGestureOnly": False,
        "unlabeledCanvasOnly": False,
        "capture": ["record", "stop"],
        "monitoring": [],
        "processing": [],
        "warnings": ["storage"],
        "record_in_scroll_only": False,
        "warnings_visible": True,
    }
    base.update(overrides)
    return base


class TCP12905(unittest.TestCase):
    def assert_contract(self, result, evidence="p129-tc05"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P129-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Nonvisual interaction")
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Perform the core phase task using accessibility navigation and spoken state information.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Expose usable names, order, values, and cancellation without relying only on color or precision gestures.",
        )
        self.assertEqual(_MODULE.NEGATIVE, "An unlabeled custom canvas as the only control must fail.")
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat camera operation, ROI selection, focus editing, and recovery export.",
        )

    def test_clean_result_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("spokenOrder=stop,record", result["preservedResults"])
        self.assertIn("cancellation=Cancel", result["preservedResults"])

    def test_negative_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(unlabeledCanvasOnly=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("p129-tc05", result["preservedResults"])

    def test_color_only_and_blank_name_are_rejected(self):
        result = evaluate(payload(
            colorOnly=True,
            controls=[
                _control("record", "Record", "ready", 0),
                _control("canvas", "", "unknown", 1),
            ],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.COLOR_OR_GESTURE, result["rejectedClaims"])
        self.assertIn(_MODULE.MISSING_NAME, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(controls=[]))
